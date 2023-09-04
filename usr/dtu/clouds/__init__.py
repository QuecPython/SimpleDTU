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
