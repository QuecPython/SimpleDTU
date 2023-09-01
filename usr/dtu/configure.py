import ql_fs
import _thread
from usr.dtu.common import Singleton


@Singleton
class Config(object):
    GET = 0x01
    SET = 0x02
    DEL = 0x03
    LOCK = _thread.allocate_lock()

    def __init__(self):
        self.path = None
        self.settings = None

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
