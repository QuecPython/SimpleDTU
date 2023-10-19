import utime
import usocket
from usr import network
from usr.logging import getLogger
from usr.threading import Queue, Thread, Condition, Lock


logger = getLogger(__name__)


class Socket(object):

    def __init__(self, host, port, timeout=5, keep_alive=None, protocol='TCP'):
        self.__host = host
        self.__port = port
        self.__ip = None
        self.__family = None
        self.__domain = None
        self.__timeout = timeout
        self.__keep_alive = keep_alive
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
        if self.__sock_type == usocket.SOCK_STREAM:
            self.__sock.connect((self.__ip, self.__port))
            if self.__timeout and self.__timeout > 0:
                self.__sock.settimeout(self.__timeout)
            if self.__keep_alive and self.__keep_alive > 0:
                self.__sock.setsockopt(usocket.SOL_SOCKET, usocket.TCP_KEEPALIVE, self.__keep_alive)

    def disconnect(self):
        if self.__sock:
            self.__sock.close()
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

    def __init__(
            self,
            domain=None,
            port=None,
            timeout=None,
            keep_alive=None
    ):
        self.__sock = Socket(domain, port, timeout=timeout, keep_alive=keep_alive)
        self.queue = Queue()
        self.__listen_thread = Thread(target=self.__listen_thread_worker)
        self.__reconn_thread = Thread(target=self.__reconnect)
        self.__reconn_cond = Condition()
        self.__reconn_mutex = Lock()

    def __listen_thread_worker(self):
        while True:
            try:
                data = self.__sock.read(1024)
                self.queue.put({'data': data})
            except Exception as e:
                if isinstance(e, OSError) and e.args[0] == 110:
                    # logger.debug('read timeout.')
                    continue
                logger.error('tcp recv error: {}'.format(e))
                with self.__reconn_cond:
                    self.reconnect()
                    self.__reconn_cond.wait_for(self.is_status_ok)

    def reconnect(self):
        with self.__reconn_mutex:
            self.__reconn_thread.start()

    def __reconnect(self):
        while True:
            logger.info('connecting...')
            with self.__reconn_cond:
                network.wait_network_ready()
                self.__disconnect()
                if self.connect():
                    self.__reconn_cond.notify_all()
                    logger.info('connect successfully.')
                    break
            utime.sleep(10)

    def __disconnect(self):
        try:
            self.__sock.disconnect()
        except Exception as e:
            logger.error('socket disconnect failed: {}'.format(e))
            return False
        return True

    def connect(self):
        try:
            self.__sock.connect()
        except Exception as e:
            logger.error('socket connect failed: {}'.format(e))
            return False
        return True

    def listen(self):
        self.__listen_thread.start()

    def close(self):
        self.__listen_thread.stop()
        self.__reconn_thread.stop()
        self.__disconnect()

    def is_status_ok(self):
        return self.__sock.is_status_ok()

    def send(self, data):
        if self.is_status_ok():
            return self.__sock.write(data)
        else:
            self.reconnect()
            return False

    def recv(self):
        return self.queue.get()
