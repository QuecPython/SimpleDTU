from usr.serial import Serial
from usr.mqttIot import MqttIot
from usr.socketIot import SocketIot
from usr.logging import getLogger
from usr.configure import Configure
from usr.threading import Thread


logger = getLogger(__name__)


class DTU(object):

    def __init__(self, name):
        self.name = name
        self.config = Configure()

    def __str__(self):
        return '<DTU \"{}\">'.format(self.name)

    @property
    def serial(self):
        __serial__ = getattr(self, '__serial__', None)
        if __serial__ is None:
            __serial__ = Serial(**self.config.get('uart_config'))
            __serial__.open()
            setattr(self, '__serial__', __serial__)
        return __serial__

    def __create_cloud(self):
        cloud_type = self.config.get('system_config.cloud')
        if cloud_type == "mqtt":
            mqtt_config = self.config.get('mqtt_private_cloud_config')
            cloud = MqttIot(**mqtt_config)
        elif cloud_type == "tcp":
            socket_config = self.config.get('socket_private_cloud_config')
            cloud = SocketIot(**socket_config)
        else:
            raise ValueError('\"{}\" not supported now!'.format(cloud_type))
        cloud.connect()
        cloud.listen()
        return cloud

    @property
    def cloud(self):
        cloud = getattr(self, '__cloud__', None)
        if cloud is None:
            cloud = self.__create_cloud()
            setattr(self, '__cloud__', cloud)
        return cloud

    def run(self):
        logger.info('{} run forever.'.format(self))
        # 启动上行数据处理线程
        logger.info('start up transaction worker thread {}.'.format(Thread.get_current_thread_ident()))
        Thread(target=self.up_transaction_handler).start()
        # 启动下行数据处理线程
        logger.info('start down transaction worker thread {}.'.format(Thread.get_current_thread_ident()))
        Thread(target=self.down_transaction_handler).start()

    def down_transaction_handler(self):
        while True:
            try:
                msg = self.cloud.recv()
                logger.info('down transfer msg: {}'.format(msg['data']))
                self.serial.write(msg['data'])
            except Exception as e:
                logger.error('down transfer error: {}'.format(e))

    def up_transaction_handler(self):
        while True:
            try:
                data = self.serial.read(1024)
                if data:
                    logger.info('up transfer msg: {}'.format(data))
                    if isinstance(self.cloud, SocketIot):
                        msg = [data]
                    elif isinstance(self.cloud, MqttIot):
                        msg = ['up', data]
                    else:
                        raise TypeError('unknow cloud type.')
                    self.cloud.send(*msg)
            except Exception as e:
                logger.error('up transfer error: {}'.format(e))
