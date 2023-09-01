from usr.dtu.serial import Serial
from usr.dtu.configure import Config
from usr.dtu.common import Thread, Condition
from usr.dtu.clouds import CloudFactory
from usr.dtu.logging import getLogger

logger = getLogger(__name__)


class Dtu(object):

    def __init__(self, name):
        self.name = name
        self.config = Config()
        self.upload_thread = Thread(target=self.upload_thread_worker)
        self.download_thread = Thread(target=self.download_thread_worker)

    def __repr__(self):
        return '<Dtu "{}">'.format(self.name)

    @property
    def cloud(self):
        __cloud__ = getattr(self, '__cloud__', None)
        if __cloud__ is None:
            __cloud__ = CloudFactory.create()
            setattr(self, '__cloud__', __cloud__)
        return __cloud__

    @property
    def serial(self):
        __serial__ = getattr(self, '__serial__', None)
        if __serial__ is None:
            __serial__ = Serial(**self.config['UART'])
            setattr(self, '__serial__', __serial__)
        return __serial__

    def run(self):
        self.serial.init()
        self.cloud.init()
        self.upload_thread.start()
        self.download_thread.start()
        logger.info('Dtu run successfully!')

    def download_thread_worker(self):
        print('dtu start download thread: {}'.format(self.download_thread))
        while True:
            payload = self.cloud.recv()
            logger.info('down transfer msg: {}'.format(payload))
            self.serial.write(payload['data'])

    def upload_thread_worker(self):
        print('dtu start upload thread: {}'.format(self.upload_thread))
        while True:
            data = self.serial.read(1024)
            logger.info('up transfer msg: {}'.format(data))
            try:
                self.cloud.send(data)
            except Exception as e:
                logger.error('cloud send error: {}'.format(e))
                self.cloud.init()
