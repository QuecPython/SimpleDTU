from usr.dtu.configure import Config
from usr.dtu.clouds.mqttIot import MqttIot
from usr.dtu.clouds.socketIot import SocketIot


class CloudFactory(object):
    config = Config()
    # cloud supported now!
    DEFAULT_CLOUDS = {
        'MQTT': MqttIot,
        'SOCKET': SocketIot
    }

    @classmethod
    def create(cls):
        cloud_type = cls.config['SYSTEM.CLOUD']
        cloud_params = cls.config['PARAMS.{}'.format(cloud_type)]
        cloud_cls = cls.DEFAULT_CLOUDS.get(cloud_type)
        if cloud_cls is None:
            raise TypeError(
                'cloud \"{}\" not supported now!'
                'maybe you wanna register one using `CloudFactory.register` method.'.format(cloud_type)
            )
        return cloud_cls(**cloud_params)

    @classmethod
    def register(cls, name, class_):
        cls.DEFAULT_CLOUDS[name] = class_
