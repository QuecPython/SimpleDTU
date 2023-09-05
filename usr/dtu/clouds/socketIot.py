import utime
import usocket
from usr.dtu.common import Thread, Queue, Condition, Lock
from usr.dtu.logging import getLogger


logger = getLogger(__name__)


class Socket(object):

    def __init__(self, host, port, timeout=5, protocol='TCP'):
        self.__host = host
        self.__port = port
        self.__ip = None
        self.__family = None
        self.__domain = None
        self.__timeout = timeout
        self.__sock = None
        if protocol == 'TCP':
            self.__sock_type = usocket.SOCK_STREAM
        else:
            self.__sock_type = usocket.SOCK_DGRAM

    def __str__(self):
        if self.__sock is None:
            return '<Socket Unbound>'
        return '<{}({}:{})>'.format(
            'TCP' if self.__sock_type == usocket.SOCK_STREAM else 'UDP',
            self.__ip,
            self.__port
        )

    def __init_args(self):
        rv = usocket.getaddrinfo(self.__host, self.__port)
        if not rv:
            raise ValueError('DNS detect error for addr: {},{}.'.format(self.__host, self.__port))
        self.__family = rv[0][0]
        self.__domain = rv[0][3]
        self.__ip, self.__port = rv[0][4]

    def connect(self):
        self.__init_args()
        self.__sock = usocket.socket(self.__family, self.__sock_type)
        self.__sock.settimeout(self.__timeout)
        if self.__sock_type == usocket.SOCK_STREAM:
            self.__sock.connect((self.__ip, self.__port))

    def disconnect(self):
        if self.__sock:
            self.__sock.close()
            logger.info('{} disconnect.'.format(self))
            self.__sock = None

    def is_status_ok(self):
        if self.__sock:
            if self.__sock_type == usocket.SOCK_STREAM:
                return self.__sock.getsocketsta() == 4
            else:
                return True
        return False

    def write(self, data):
        if self.__sock_type == usocket.SOCK_STREAM:
            flag = (self.__sock.send(data) == len(data))
        else:
            flag = (self.__sock.sendto(data, (self.__ip, self.__port)) == len(data))
        return flag

    def read(self, size=1024):
        return self.__sock.recv(size)


class SocketIot(object):
    RECONNECT_INTERVAL = 10

    def __init__(self, host, port, timeout=5, protocol='TCP'):
        self.__host = host
        self.__port = port
        self.__timeout = timeout
        self.__protocol = protocol

        self.__sock = None
        self.__queue = Queue()
        self.__recv_thread = Thread(target=self.__recv_thread_worker)
        self.__reconnect_thread = Thread(target=self.__reconnect_thread_worker)
        self.__reconnect_lock = Lock()
        self.__ready = Condition()

    def __connect(self):
        self.__sock = Socket(self.__host, self.__port, self.__timeout, self.__protocol)
        self.__sock.connect()

    def __disconnect(self):
        if self.__sock:
            self.__sock.disconnect()
            self.__sock = None

    def init(self):
        logger.info('SocketIot init.')
        if self.__sock is None or not self.__sock.is_status_ok():
            try:
                self.__disconnect()
                self.__connect()
            except Exception as e:
                logger.error('{} connect error: {}'.format(self.__sock, e))
                return False
            else:
                logger.info('{} connect successfully.'.format(self.__sock))
                self.__recv_thread.start()
        return True

    def deinit(self):
        try:
            self.__reconnect_thread.stop()
            self.__recv_thread.stop()
            self.__disconnect()
        except Exception as e:
            logger.warn('SocketIot deinit error: {}'.format(e))

    def __reconnect_thread_worker(self):
        while not self.init():
            utime.sleep(self.RECONNECT_INTERVAL)
        self.__ready.notify_all()

    def __recv_thread_worker(self):
        while True:
            try:
                data = self.__sock.read()
            except Exception as e:
                if isinstance(e, OSError) and e.args[0] == 110:
                    continue
                else:
                    logger.error('{} read error: {}'.format(self, e))
                    with self.__reconnect_lock:
                        self.__reconnect_thread.start()
                    self.__ready.wait()
            else:
                logger.debug('{} recv data: {}'.format(self.__sock, data))
                self.__queue.put({'data': data})

    def recv(self):
        return self.__queue.get()

    def send(self, data):
        with self.__reconnect_lock:
            if self.__reconnect_thread.is_running():
                logger.warn('send failed because because of reconnecting.')
                return False

        try:
            is_ok = self.__sock.write(data)
        except Exception as e:
            logger.error('{} send error: {}'.format(self.__sock, e))
            is_ok = False

        if not is_ok:
            with self.__reconnect_lock:
                self.__reconnect_thread.start()

        return is_ok
