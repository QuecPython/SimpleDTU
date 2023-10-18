import usys
import utime
import _thread
import usocket
from usr import error
from usr.logging import getLogger
from usr.net_manager import NetManager


logger = getLogger(__name__)


class SocketIot(object):
    """This class is tcp socket"""
    RECONNECT_WAIT_SECONDS = 20

    def __init__(self, ip_type=None, protocol="TCP", keep_alive=None, domain=None, port=None, queue=None, error_trans=False):
        super().__init__()
        if protocol == "TCP" or protocol is None:
            self.__protocol = "TCP"
        else:
            self.__protocol = "UDP"
        if ip_type == "IPv6":
            self.__ip_type = usocket.AF_INET6
        else:
            self.__ip_type = usocket.AF_INET
        self.__port = port
        self.__domain = domain
        self.__addr = None
        self.__socket = None
        self.__socket_args = []
        self.__timeout = 50
        self.__keep_alive = keep_alive
        self.__listen_thread_id = None
        self.__init_addr()
        self.__init_socket()
        self.queue = queue
        self.error_trans = error_trans

    def __init_addr(self):
        if self.__domain is not None:
            if self.__port is None:
                self.__port = 8883 if self.__domain.startswith("https://") else 1883
            try:
                addr_info = usocket.getaddrinfo(self.__domain, self.__port)
                self.__ip = addr_info[0][-1][0]
            except Exception as e:
                usys.print_exception(e)
                raise ValueError("Domain %s DNS parsing error. %s" % (self.__domain, str(e)))
        self.__addr = (self.__ip, self.__port)

    def __init_socket(self):
        if self.__protocol == 'TCP':
            socket_type = usocket.SOCK_STREAM
            socket_proto = usocket.IPPROTO_TCP
        elif self.__protocol == 'UDP':
            socket_type = usocket.SOCK_DGRAM
            socket_proto = usocket.IPPROTO_UDP
        else:
            raise ValueError("Args method is TCP or UDP, not %s" % self.__protocol)
        self.__socket_args = (self.__ip_type, socket_type, socket_proto)

    def __connect(self):
        if self.__socket_args:
            try:
                self.__socket = usocket.socket(*self.__socket_args)
                if self.__protocol == "TCP":
                    self.__socket.connect(self.__addr)
                return True
            except Exception as e:
                usys.print_exception(e)
                return False

        return False

    def recv_thread_worker(self):
        """Read data by socket."""
        while True:
            try:
                data = self.__socket.recv(1024)
            except Exception as e:
                if isinstance(e, OSError) and e.args[0] == 110:
                    logger.debug('read timeout.')
                    continue
                logger.error('tcp listen error: {}'.format(e))
                self.put_error(error.ListenError())
                self.__socket.close()
                self.connect()
                continue
            else:
                self.queue.put((None, data))
            utime.sleep_ms(50)

    def init(self):
        self.connect()
        self.listen()

    def listen(self):
        self.__listen_thread_id = _thread.start_new_thread(self.recv_thread_worker, ())

    def connect(self):

        while True:
            # 检查注网和拨号
            if not NetManager.check_and_reconnect():
                logger.error('network status error.')
                continue

            if not self.__connect():
                logger.error('tcp connect error.')
                self.put_error(error.ConnectError())
                utime.sleep(self.RECONNECT_WAIT_SECONDS)
                continue

            if self.__keep_alive != 0:
                try:
                    self.__socket.setsockopt(usocket.SOL_SOCKET, usocket.TCP_KEEPALIVE, self.__keep_alive)
                except Exception as e:
                    logger.error("socket option set error: {}".format(e))
                    self.put_error(error.SetSocketOptError())
                    self.__socket.close()
                    continue

            self.__socket.settimeout(self.__timeout)
            logger.info('tcp connect successfully!')
            break

    def get_status(self):
        _status = -1
        if self.__socket is not None:
            try:
                if self.__protocol == "TCP":
                    socket_sta = self.__socket.getsocketsta()
                    if socket_sta in range(4):
                        # Connecting
                        _status = 1
                    elif socket_sta == 4:
                        # Connected
                        _status = 0
                    elif socket_sta in range(5, 11):
                        # Disconnect
                        _status = 2
                elif self.__protocol == "UDP":
                    _status = 0
            except Exception as e:
                usys.print_exception(e)
        return _status

    def send(self, data):
        try:
            self.__socket.write(data)
        except Exception as e:
            logger.error('tcp socket send error: {}, repare to check network.'.format(str(e)))
            self.put_error(error.TCPSendError())
            NetManager.check_and_reconnect()

    def recv(self):
        return self.queue.get()

    def put_error(self, e):
        if self.error_trans:
            self.queue.put((None, str(e)))
