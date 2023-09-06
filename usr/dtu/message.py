import ujson as json
from usr.dtu.logging import getLogger


logger = getLogger(__name__)


class FormatError(Exception):
    pass


class ValidateError(Exception):
    pass


class Message(object):
    identifier = 0x7E

    def __init__(self, payload=None):
        self.__payload = payload or {}
        self.__raw = None
        self.__crc = None

    @property
    def payload(self):
        return self.__payload

    @property
    def raw(self):
        return self.__raw

    @property
    def crc(self):
        return self.__crc

    def dump(self):
        if self.__raw is not None:
            return self.__raw
        payload = json.dumps(self.payload).encode()
        self.__crc = self.gen_crc(payload)
        body = payload + self.crc.to_bytes(1, 'big')
        self.__raw = self.identifier.to_bytes(1, 'big') + self.escape(body) + self.identifier.to_bytes(1, 'big')
        return self.__raw

    @staticmethod
    def escape(data):
        origin = b''
        for one in data:
            if one == 0x7E:
                origin += b'\x80\x02'
            elif one == 0x80:
                origin += b'\x80\x01'
            else:
                origin += one.to_bytes(1, 'big')
        return origin

    @staticmethod
    def revert(data):
        origin = b''
        index = 0
        while index <= len(data) - 1:
            one = data[index]
            if one == 0x80:
                if data[index + 1] == 0x01:
                    origin += b'\x80'
                elif data[index + 1] == 0x02:
                    origin += b'\x7E'
                else:
                    raise FormatError('revert error at {} bytes, 0x01 or 0x02 should be followed.'.format(index))
                index += 2
            else:
                origin += one.to_bytes(1, 'big')
                index += 1
        return origin

    @classmethod
    def load(cls, data):
        if len(data) < 5:
            raise FormatError('message length should not less than 14, got {}.'.format(len(data)))

        if data[0] != cls.identifier or data[-1] != cls.identifier:
            raise FormatError('identifier error, not a valid message.')

        data = cls.revert(data[1:-1])  # strip head and tail's identifier `0x7E` then to revert escape
        crc = data[-1]
        if crc != cls.gen_crc(data[:-1]):
            raise ValidateError('CRC check error.')

        payload = json.loads(data[:-1])
        self = cls(payload=payload)
        self.__crc = crc
        return self

    @staticmethod
    def gen_crc(data):
        crc = data[0]
        for one in data[1:]:
            crc ^= one
        return crc

    def __str__(self):
        data = ''
        data += 'header: {}\n'.format(self.identifier)
        data += 'payload: {}\n'.format(self.payload)
        data += 'crc: {}\n'.format(self.crc)
        data += 'tail: {}\n'.format(self.identifier)
        return data


class Parser(object):

    def __init__(self, load=True):
        self.buffer = b''
        self.message_list = []
        self.__load = load

    def parse(self, data):
        self.buffer += data

        while True:
            header_index = self.buffer.find(b'\x7E')
            if header_index == -1:
                self.clear()
                break

            tail_index = self.buffer.find(b'\x7E', header_index+1)
            if tail_index == -1:
                break  # waiting for more bytes

            if tail_index - header_index == 1:
                self.buffer = self.buffer[tail_index:]
                continue

            try:
                if self.__load:
                    msg = Message.load(self.buffer[header_index:tail_index+1])
                else:
                    msg = self.buffer[header_index:tail_index+1]
                self.message_list.append(msg)
            except Exception as e:
                logger.error('message parse error: {}'.format(e))

            self.buffer = self.buffer[tail_index+1:]

    @property
    def messages(self):
        rv, self.message_list = self.message_list, []
        return rv

    def clear(self):
        self.buffer = b''
