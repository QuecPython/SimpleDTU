import usocket
from usr.dtu.common import Thread, Queue
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
            print('{} disconnect.'.format(self))
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

    def __init__(self, host, port, timeout=5, protocol='TCP'):
        self.__host = host
        self.__port = port
        self.__timeout = timeout
        self.__protocol = protocol

        self.__sock = None
        self.__recv_thread = Thread(target=self.__recv_thread_worker)
        self.__queue = Queue()

    def init(self):
        if self.__sock is None:
            self.__sock = Socket(
                self.__host,
                self.__port,
                self.__timeout,
                self.__protocol
            )
        else:
            if self.__sock.is_status_ok():
                return
            else:
                self.__sock.disconnect()
                self.__recv_thread.stop()
        self.__sock.connect()
        self.__recv_thread.start()

    def __recv_thread_worker(self):
        while True:
            try:
                data = self.__sock.read()
            except Exception as e:
                if isinstance(e, OSError) and e.args[0] == 110:
                    continue
                else:
                    print('{} read error: {}, recv thread break.'.format(self, e))
                    break
            else:
                print('{} recv data: {}'.format(self.__sock, data))
                self.__queue.put({'data': data})

    def recv(self, timeout=-1):
        return self.__queue.get(timeout=timeout)

    def send(self, data):
        return self.__sock.write(data)
