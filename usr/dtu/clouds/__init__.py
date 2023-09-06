from usr.dtu.common import Thread, Condition
from usr.dtu.network import NetMonitor
from usr.dtu.clouds.mqttIot import MqttIot
from usr.dtu.clouds.socketIot import SocketIot


class CloudFactory(object):

    # cloud supported now!
    DEFAULT_CLOUDS = {
        'MQTT': MqttIot,
        'SOCKET': SocketIot
    }

    @classmethod
    def create(cls, config):
        cloud_type = config['SYSTEM.CLOUD']
        cloud_params = config['PARAMS.{}'.format(cloud_type)]
        cloud_cls = cls.DEFAULT_CLOUDS.get(cloud_type)
        if cloud_cls is None:
            raise TypeError(
                'cloud \"{}\" not supported now!'
                'maybe you wanna register one using `CloudFactory.register` method.'.format(cloud_type)
            )
        return cloud_cls(**cloud_params)

    @classmethod
    def register(cls, name, class_):
        if name in cls.DEFAULT_CLOUDS:
            raise ValueError('\"{}\" already registered!'.format(name))
        cls.DEFAULT_CLOUDS[name] = class_


class CloudReconnectThread(object):

    def __init__(self):
        self.__cloud = None
        self.__thread = Thread(target=self.__cloud_reconnect_thread_worker)
        self.__cond = Condition()
        self.start = self.__thread.start
        self.stop = self.__thread.stop
        self.is_running = self.__thread.is_running

    def add_cloud(self, cloud):
        self.__cloud = cloud

    def start(self):
        if self.__cloud is None:
            raise ValueError('cloud can not be  None, use `add_cloud` method.')
        self.__thread.start()

    def __cloud_reconnect_thread_worker(self):
        while True:
            self.__cond.wait()
            NetMonitor.wait_network_ready()
            self.__cloud.init()

    def notify(self):
        self.__cond.notify()