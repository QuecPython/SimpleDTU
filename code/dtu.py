import _thread
from queue import Queue
from usr.serial import Serial
from usr.mqttIot import MqttIot
from usr.socketIot import SocketIot
from usr.logging import getLogger
from usr.configure import Configure


logger = getLogger(__name__)


class DTU(object):

    def __init__(self, name):
        self.name = name
        self.queue = Queue()  # DTU应用与MQTT、TCP客户端下行数据交互队列
        self.config = Configure()
        self.serial = None
        self.cloud = None

    def init(self):
        self.serial = Serial(**self.config.get('uart_config'))
        self.serial.open()

        cloud_type = self.config.get('system_config.cloud')
        if cloud_type == "mqtt":
            mqtt_config = self.config.get('mqtt_private_cloud_config')
            self.cloud = MqttIot(
                mqtt_config['client_id'],
                mqtt_config['server'],
                port=mqtt_config['port'],
                user=mqtt_config['user'],
                password=mqtt_config['password'],
                keepalive=mqtt_config['keepalive'],
                clean_session=mqtt_config['clean_session'],
                qos=mqtt_config['qos'],
                subscribe_topic=mqtt_config['subscribe'],
                publish_topic=mqtt_config['publish'],
                queue=self.queue,
                error_trans=True
            )
        elif cloud_type == "tcp":
            socket_config = self.config.get('socket_private_cloud_config')
            self.cloud = SocketIot(
                ip_type=socket_config['ip_type'],
                keep_alive=socket_config['keep_alive'],
                domain=socket_config['domain'],
                port=socket_config['port'],
                queue=self.queue,
                error_trans=True
            )
        else:
            raise ValueError('{} unsupported now.'.format(cloud_type))
        self.cloud.init()

    def run(self):
        self.init()
        # 启动上行数据处理线程
        self.up_transaction()
        # 启动下行数据处理线程
        self.down_transaction()

    def down_transaction(self):
        logger.info('start down transaction worker thread {}.'.format(_thread.get_ident()))
        _thread.start_new_thread(self.down_transaction_handler, ())

    def down_transaction_handler(self):
        while True:
            topic, data = self.cloud.recv()
            logger.info('down transfer msg: {}'.format(data))
            self.serial.write(data)

    def up_transaction(self):
        logger.info('start up transaction worker thread {}.'.format(_thread.get_ident()))
        _thread.start_new_thread(self.up_transaction_handler, ())

    def up_transaction_handler(self):
        while True:
            data = self.serial.read(1024, timeout=100)
            if data:
                logger.info('up transfer msg: {}'.format(data))
                self.cloud.send(data)
