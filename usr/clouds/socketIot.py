from usr.common.socket import Socket
from usr.common.threading import Thread, Queue
from usr.common.logging import getLogger


logger = getLogger(__name__)


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
            self.__recv_thread.stop()
            self.__disconnect()
        except Exception as e:
            logger.warn('SocketIot deinit error: {}'.format(e))

    def __recv_thread_worker(self):
        while True:
            try:
                msg = self.__sock.read()
            except Exception as e:
                if isinstance(e, OSError) and e.args[0] == 110:
                    continue
                else:
                    logger.error('{} read error: {}'.format(self, e))
                    self.__queue.put(None)
                    break
            else:
                logger.debug('{} recv msg: {}'.format(self.__sock, msg))
                self.__queue.put({'msg': msg})

    def recv(self):
        return self.__queue.get()

    def send(self, data, transparent=False):
        try:
            if transparent:
                msg = data
            else:
                msg = data['msg']
            is_ok = self.__sock.write(msg)
        except Exception as e:
            logger.error('{} send error: {}'.format(self.__sock, e))
            is_ok = False

        return is_ok
