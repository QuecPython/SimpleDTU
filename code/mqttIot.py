from umqtt import MQTTClient
from usr import network
from usr.logging import getLogger
from usr.threading import Queue, Thread, Condition, Lock


logger = getLogger(__name__)


class MqttIot(object):

    def __init__(self, *args, **kwargs):
        """init umqtt.MQTTClient instance.
        args:
            client_id - 客户端 ID，字符串类型，具有唯一性。
            server - 服务端地址，字符串类型，可以是 IP 或者域名。
        kwargs:
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
            subscribe - 订阅主题。
            publish - 发布主题。
        """
        self.args = args
        self.kwargs = kwargs
        self.clean_session = self.kwargs.pop('clean_session', True)
        self.qos = self.kwargs.pop('qos', 0)
        self.subscribe_topic = self.kwargs.pop('subscribe', {})
        self.publish_topic = self.kwargs.pop('publish', {})
        self.__queue = Queue()
        self.kwargs.setdefault('reconn', False)  # 禁用内部重连机制
        self.__cli = None
        self.__listen_thread = Thread(target=self.__listen_thread_worker)
        self.__reconn_thread = Thread(target=self.__reconnect)
        self.__reconn_cond = Condition()
        self.__reconn_mutex = Lock()

    def __callback(self, topic, data):
        self.__queue.put({'topic': topic, 'data': data})

    def __listen_thread_worker(self):
        while True:
            try:
                self.__cli.wait_msg()
            except Exception as e:
                logger.error('mqtt listen error: {}'.format(str(e)))
                with self.__reconn_cond:
                    self.reconnect()
                    self.__reconn_cond.wait_for(self.is_status_ok)

    def reconnect(self):
        with self.__reconn_mutex:
            self.__reconn_thread.start()

    def __reconnect(self):
        while True:
            network.wait_network_ready()
            logger.info('mqtt connecting...')
            with self.__reconn_cond:
                self.__disconnect()
                if self.connect():
                    self.__reconn_cond.notify_all()
                    logger.info('mqtt connect successfully.')
                    break

    def __disconnect(self):
        try:
            self.__cli.disconnect()
            self.__cli = None
        except Exception as e:
            logger.error('mqtt disconnect failed: {}'.format(e))
            return False
        return True

    def connect(self):
        try:
            self.__cli = MQTTClient(*self.args, **self.kwargs)
            self.__cli.connect(clean_session=self.clean_session)
        except Exception as e:
            logger.error('mqtt connect failed. {}'.format(str(e)))
            return False
        else:
            try:
                self.__cli.set_callback(self.__callback)
                for topic in self.subscribe_topic.values():
                    logger.info('subscribe topic: {}'.format(topic))
                    self.__cli.subscribe(topic, self.qos)
            except Exception as e:
                logger.error('mqtt subscribe failed. {}'.format(str(e)))
                return False
        return True

    def listen(self):
        self.__listen_thread.start()

    def close(self):
        self.__listen_thread.stop()
        self.__reconn_thread.stop()
        self.__disconnect()

    def is_status_ok(self):
        return self.__cli is not None and self.__cli.get_mqttsta() == 0

    def send(self, topic_id, data):
        if self.is_status_ok():
            return self.__cli.publish(self.publish_topic[topic_id], data, qos=self.qos)
        else:
            self.reconnect()
            return False

    def recv(self):
        return self.__queue.get()
