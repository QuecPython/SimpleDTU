import uos
import ql_fs
from usr.dtu.common import Singleton, Lock


DEFAULT_CONFIG = {
    "SYSTEM": {
        "CLOUD": "SOCKET"
    },
    "PARAMS": {
        "MQTT": {
            "server": "mq.tongxinmao.com",
            "port": 18830,
            "client_id": "txm_1682300809",
            "user": "",
            "password": "",
            "clean_session": True,
            "qos": 0,
            "keepalive": 60,
            "subscribe": "/public/TEST/test",
            "publish": "/public/TEST/test"
        },
        "SOCKET": {
            "host": "v5.idcfengye.com",
            "port": 10033,
            "timeout": 5,
            "protocol": "TCP"
        }
    },
    "UART": {
        "port": 2,
        "baudrate": 115200,
        "bytesize": 8,
        "parity": 0,
        "stopbits": 1,
        "flowctl": 0,
        "rs485_pin": None
    }
}


@Singleton
class Configure(object):
    GET = 0x01
    SET = 0x02
    DEL = 0x03
    LOCK = Lock()

    def __init__(self):
        self.path = None
        self.settings = DEFAULT_CONFIG

    def reset(self, save=True):
        with self.LOCK:
            self.settings = DEFAULT_CONFIG
            if self.path and ql_fs.path_exists(self.path):
                uos.remove(self.path)
                if save:
                    ql_fs.touch(self.path, self.settings)

    def read_from_json(self, path):
        self.path = path
        self.settings = ql_fs.read_json(path)

    def save(self):
        with self.LOCK:
            ql_fs.touch(self.path, self.settings)

    def get(self, key):
        with self.LOCK:
            return self.execute(self.settings, key.split('.'), operate=self.GET)

    def __getitem__(self, item):
        return self.get(item)

    def set(self, key, value):
        with self.LOCK:
            return self.execute(self.settings, key.split('.'), value=value, operate=self.SET)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def delete(self, key):
        with self.LOCK:
            return self.execute(self.settings, key.split('.'), operate=self.DEL)

    def __delitem__(self, key):
        return self.delete(key)

    def execute(self, dict_, keys, value=None, operate=None):
        if self.settings is None:
            raise ValueError('settings not loaded. pls use `Config.read_from_json` to load settings from a json file.')

        key = keys.pop(0)

        if len(keys) == 0:
            if operate == self.GET:
                return dict_[key]
            elif operate == self.SET:
                dict_[key] = value
            elif operate == self.DEL:
                del dict_[key]
            return

        if key not in dict_:
            if operate == self.SET:
                dict_[key] = {}  # auto create sub items recursively.
            else:
                return

        return self.execute(dict_[key], keys, value=value, operate=operate)
