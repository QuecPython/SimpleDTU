from usr.dtu.serial import Serial
from usr.dtu.configure import Configure
from usr.dtu.common import Thread, Condition, TimeoutError, Event
from usr.dtu.clouds import CloudFactory
from usr.dtu.logging import getLogger
from usr.dtu.network import PubSub, NetMonitor
from usr.dtu.message import Message, Parser


logger = getLogger(__name__)


class Dtu(object):

    def __init__(self, name):
        self.name = name
        self.config = Configure()
        self.upload_thread = Thread(target=self.upload_thread_worker)
        self.download_thread = Thread(target=self.download_thread_worker)
        PubSub.subscribe(NetMonitor.SIM_STATUS_TOPIC, self.__sim_status_callback)
        PubSub.subscribe(NetMonitor.NET_STATUS_TOPIC, self.__net_status_callback)
        self.transparent_event = Event()

    def __repr__(self):
        return '<Dtu "{}">'.format(self.name)

    def __sim_status_callback(self, state):
        if state == 1:
            self.serial.write(b'SIM CARD INSERT.\n')
        elif state == 2:
            self.serial.write(b'SIM CARD REMOVE.\n')
        else:
            self.serial.write(b'SIM CARD STATUS UNKNOW.\n')

    def __net_status_callback(self, args):
        pdp, state = args[0], args[1]
        if state == 0:
            self.serial.write(('NETWORK DISCONNECTED, PDP: {}.\n'.format(pdp)).encode())
        else:
            self.serial.write(('NETWORK CONNECTED, PDP: {}.\n'.format(pdp)).encode())

    @property
    def cloud(self):
        __cloud__ = getattr(self, '__cloud__', None)
        if __cloud__ is None:
            __cloud__ = CloudFactory.create(self.config)
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
        self.init_transparent_mode()
        self.serial.init()
        self.cloud.init()
        self.upload_thread.start()
        self.download_thread.start()

    def init_transparent_mode(self):
        if self.config['SYSTEM.TRANSPARENT']:
            self.transparent_event.set()
        else:
            self.transparent_event.clear()

    def download_thread_worker(self):
        logger.info('dtu start download thread: {}'.format(self.download_thread))
        while True:
            payload = self.cloud.recv()
            logger.info('down transfer msg: {}'.format(payload))
            if self.transparent_event.is_set():
                self.serial.write(payload['msg'])
            else:
                self.serial.write(Message(payload).dump())

    def upload_thread_worker(self):
        logger.info('dtu start upload thread: {}'.format(self.upload_thread))
        parser = Parser(load=True)
        while True:
            try:
                data = self.serial.read(1024, timeout=10)
                logger.info('up transfer msg: {}'.format(data))
            except TimeoutError:
                parser.clear()
            else:
                if data == b'+++++':
                    self.transparent_event.set()
                    self.config['SYSTEM.TRANSPARENT'] = True
                    self.config.save()
                elif data == b'-----':
                    self.transparent_event.clear()
                    self.config['SYSTEM.TRANSPARENT'] = False
                    self.config.save()
                    parser.clear()
                else:
                    if self.transparent_event.is_set():
                        self.cloud.send(data, transparent=True)
                    else:
                        parser.parse(data)
                        for msg in parser.messages:
                            if not self.cloud.send(msg.payload, transparent=False):
                                # do something?
                                pass
