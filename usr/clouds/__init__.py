from usr.common.threading import Thread, Lock
from usr.common.network import NetMonitor
from usr.clouds.mqttIot import MqttIot
from usr.clouds.socketIot import SocketIot


class CloudFactory(object):

    # cloud supported now!
    DEFAULT_CLOUDS = {
        'MQTT': MqttIot,
        'SOCKET': SocketIot
    }

    @classmethod
    def create(cls, config):
        cloud_type = config['SYSTEM.CLOUD']
        cloud_params = config['CLOUD_PARAMS.{}'.format(cloud_type)]
        cloud_cls = cls.DEFAULT_CLOUDS.get(cloud_type)
        if cloud_cls is None:
            raise TypeError(
                'cloud \"{}\" not supported now!'
                'maybe you wanna register one using `CloudFactory.register` method.'.format(cloud_type)
            )
        cloud = cloud_cls(**cloud_params)
        cloud.reconnect_thread = CloudReconnectThread(cloud)
        return cloud

    @classmethod
    def register(cls, name, class_):
        if name in cls.DEFAULT_CLOUDS:
            raise ValueError('\"{}\" already registered!'.format(name))
        cls.DEFAULT_CLOUDS[name] = class_


class CloudReconnectThread(object):

    def __init__(self, cloud):
        self.__cloud = cloud
        self.__thread = Thread(target=self.__cloud_reconnect_thread_worker)
        self.start = self.__thread.start
        self.stop = self.__thread.stop
        self.__reconnect_lock = Lock()

    def add_cloud(self, cloud):
        self.__cloud = cloud

    def start(self):
        if self.__cloud is None:
            raise ValueError('cloud can not be  None, use `add_cloud` method.')
        with self.__reconnect_lock:
            self.__thread.start()

    def stop(self):
        with self.__reconnect_lock:
            self.__thread.stop()

    def is_running(self):
        with self.__reconnect_lock:
            return self.__thread.is_running()

    def __cloud_reconnect_thread_worker(self):
        while True:
            NetMonitor.wait_network_ready()
            if self.__cloud.init():
                break
