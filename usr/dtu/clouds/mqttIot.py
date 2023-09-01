import utime
from umqtt import MQTTClient
from usr.dtu.common import Queue, Thread, Condition, Lock
from usr.dtu.logging import getLogger

logger = getLogger(__name__)


class MqttIot(object):
    RECONNECT_INTERVAL = 10

    def __init__(self, client_id, server, **options):
        """init umqtt.MQTTClient instance.
        args:
            client_id - 客户端 ID，字符串类型，具有唯一性。
            server - 服务端地址，字符串类型，可以是 IP 或者域名。
        options:
            port - 服务器端口（可选），整数类型，默认为1883，请注意，MQTT over SSL/TLS的默认端口是8883。
            user - （可选) 在服务器上注册的用户名，字符串类型。
            password - （可选) 在服务器上注册的密码，字符串类型。
            keepalive - （可选）客户端的keepalive超时值，整数类型，默认为0。
            ssl - （可选）是否使能 SSL/TLS 支持，布尔值类型。
            ssl_params - （可选）SSL/TLS 参数，字符串类型。
            reconn - （可选）控制是否使用内部重连的标志，布尔值类型，默认开启为True。
            version - （可选）选择使用mqtt版本，整数类型，version=3开启MQTTv3.1，默认version=4开启MQTTv3.1.1。
            clean_session - 布尔值类型，可选参数，一个决定客户端类型的布尔值。 如果为True，那么代理将在其断开连接时删除有关此客户端的所有信息。
                如果为False，则客户端是持久客户端，当客户端断开连接时，订阅信息和排队消息将被保留。默认为True。
            qos - MQTT消息服务质量（默认0，可选择0或1）.
                整数类型 0：发送者只发送一次消息，不进行重试 1：发送者最少发送一次消息，确保消息到达Broker。
            subscribe_topic - 订阅主题。
            publish_topic - 发布主题。
        """
        self.__client_id = client_id
        self.__server = server

        options['reconn'] = False  # 禁用内部重连机制
        self.__clean_session = options.pop('clean_session', True)
        self.__qos = options.pop('qos', 0)
        self.__subscribe_topic = options.pop('subscribe', '/public/test')
        self.__publish_topic = options.pop('publish', '/public/test')

        self.__options = options
        self.__queue = Queue()
        self.__cli = None
        self.__recv_thread = Thread(target=self.__recv_thread_worker)
        self.__reconnect_thread = Thread(target=self.__reconnect_thread_worker)
        self.__reconnect_lock = Lock()
        self.__ready = Condition()

    def __disconnect(self):
        if self.__cli:
            self.__cli.disconnect()
            self.__cli = None

    def __connect(self):
        self.__cli = MQTTClient(
            self.__client_id,
            self.__server,
            **self.__options
        )
        self.__cli.set_callback(self.__callback)
        self.__cli.connect(self.__clean_session)
        self.__cli.subscribe(self.__subscribe_topic, self.__qos)

    def init(self):
        if self.__cli is None or self.__cli.get_mqttsta() != 0:
            try:
                self.__disconnect()
                self.__connect()
            except Exception as e:
                logger.error('mqtt connect error: {}'.format(e))
                return False
            else:
                logger.info('mqtt connect successfully.')
                self.__recv_thread.start()
        return True

    def deinit(self):
        try:
            self.__reconnect_thread.stop()
            self.__recv_thread.stop()
            self.__disconnect()
        except Exception as e:
            logger.warn('MqttIot deinit error: {}'.format(e))

    def __callback(self, topic, data):
        self.__queue.put({'topic': topic, 'data': data})

    def __recv_thread_worker(self):
        while True:
            try:
                self.__cli.wait_msg()
            except Exception as e:
                logger.error('mqtt listen error: {}, try reconnecting.'.format(str(e)))
                with self.__reconnect_lock:
                    self.__reconnect_thread.start()
                self.__ready.wait()

    def __reconnect_thread_worker(self):
        while not self.init():
            utime.sleep(self.RECONNECT_INTERVAL)
        self.__ready.notify_all()

    def recv(self, timeout=-1):
        return self.__queue.get(timeout=timeout)

    def send(self, data):

        # check if reconnect thread is running
        with self.__reconnect_lock:
            if self.__reconnect_thread.is_running():
                logger.warn('send failed because mqtt is reconnecting.')
                return False

        # try to publish, we catch all exceptions and check the return value for `MQTTClient.publish`.
        try:
            is_ok = self.__cli.publish(self.__publish_topic, data)
        except Exception as e:
            logger.error('mqtt send error: {}'.format(e))
            is_ok = False

        if not is_ok:
            with self.__reconnect_lock:
                # try to start reconnect thread.
                # if the thread is running, we do nothing.(`start` method will check running status.)
                self.__reconnect_thread.start()

        return is_ok
