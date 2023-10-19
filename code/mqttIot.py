"""
MQTT客户端抽象类
"""
import _thread
import utime
from umqtt import MQTTClient
from usr.logging import getLogger
from usr.net_manager import NetManager
from usr.threading import Queue

logger = getLogger(__name__)


class MqttIot(object):
    RECONNECT_WAIT_SECONDS = 20

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
            subscribe_topic - 订阅主题。
            publish_topic - 发布主题。
            queue - MQTT下行数据透传队列。
            error_trans - 串口吐异常信息(开启True，关闭False，默认False)
        """
        self.clean_session = kwargs.pop('clean_session', True)
        self.qos = kwargs.pop('qos', 0)
        self.subscribe_topic = kwargs.pop('subscribe_topic', '/public/test')
        self.publish_topic = kwargs.pop('publish_topic', '/public/test')
        self.queue = Queue()
        self.error_trans = kwargs.pop('error_trans', False)

        kwargs.setdefault('reconn', False)  # 禁用内部重连机制
        self.cli = MQTTClient(*args, **kwargs)

    def init(self):
        self.cli.set_callback(self.callback)
        self.connect()
        self.listen()

    def callback(self, topic, data):
        self.queue.put({'topic': topic, 'data': data})

    def put_error(self, e):
        if self.error_trans:
            self.queue.put((None, str(e)))

    def connect(self):

        while True:
            # 重连
            try:
                self.cli.connect()
            except Exception as e:
                logger.error('mqtt connect failed. {}'.format(str(e)))
                utime.sleep(self.RECONNECT_WAIT_SECONDS)
                continue
            # 订阅
            try:
                self.cli.subscribe(self.subscribe_topic, self.qos)
            except Exception as e:
                logger.error('mqtt subscribe failed. {}'.format(str(e)))
                utime.sleep(self.RECONNECT_WAIT_SECONDS)
                continue
            logger.info('mqtt connect successfully!')
            break

    def listen(self):
        _thread.start_new_thread(self.listen_thread_worker, ())

    def listen_thread_worker(self):
        while True:
            try:
                self.cli.wait_msg()
            except Exception as e:
                logger.error('mqtt listen error continue to reconnect. {}'.format(str(e)))
                self.cli.close()
                self.connect()

    def recv(self):
        return self.queue.get()

    def send(self, data):
        try:
            if not self.cli.publish(self.publish_topic, data):
                logger.error('publish failed.')
        except Exception as e:
            logger.error('publish failed with error: {}, prepare to check network.'.format(e))
