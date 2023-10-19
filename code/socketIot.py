import usocket
from usr.logging import getLogger
from usr.threading import Queue, Thread


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
        self.__recv_thread = Thread(target=self.recv_thread_worker)

    def recv_thread_worker(self):
        """Read data by socket."""
        while True:
            try:
                data = self.__sock.read(1024)
                self.queue.put({'data': data})
            except Exception as e:
                if isinstance(e, OSError) and e.args[0] == 110:
                    logger.debug('read timeout.')
                    continue
                logger.error('tcp listen error: {}'.format(e))
                break

    def connect(self):
        try:
            self.__sock.connect()
        except Exception as e:
            logger.error('socket connect failed: {}'.format(e))
        else:
            self.__recv_thread.start()

    def disconnect(self):
        self.__recv_thread.stop()
        self.__sock.disconnect()

    def is_status_ok(self):
        return self.__sock.is_status_ok()

    def send(self, data):
        try:
            self.__sock.write(data)
        except Exception as e:
            logger.error('tcp socket send error: {}, prepare to check network.'.format(str(e)))

    def recv(self):
        return self.queue.get()
