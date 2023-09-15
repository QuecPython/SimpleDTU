"""
utils for QuecPython development.
@File : utils.py
@Author : Dustin Wei
@Email : dustin.wei@quectel.com
@Date : 2023/9/14 10:12 
"""


class Singleton(object):
    def __init__(self, cls):
        self.cls = cls
        self.instance = None

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = self.cls(*args, **kwargs)
        return self.instance

    def __repr__(self):
        return self.cls.__repr__()
