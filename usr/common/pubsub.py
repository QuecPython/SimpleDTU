"""
utils for QuecPython development, include:
    -   Thread synchronization and asynchronous
    -   Thread Pool Executor
@File : thread.py
@Author : Dustin Wei
@Email : dustin.wei@quectel.com
@Date : 2023/9/14 10:15
"""
from usr.common.threading import Lock, Thread


class PubSub(object):
    TOPIC_MAP = {}
    PUBSUB_LOCK = Lock()

    @classmethod
    def subscribe(cls, topic, callback):
        with cls.PUBSUB_LOCK:
            if topic not in cls.TOPIC_MAP:
                cls.TOPIC_MAP[topic] = [callback]
            else:
                cls.TOPIC_MAP[topic].append(callback)

    @classmethod
    def publish(cls, topic, *args, **kwargs):
        with cls.PUBSUB_LOCK:
            for cb in cls.TOPIC_MAP.get(topic, []):
                Thread(target=cb, args=args, kwargs=kwargs).start()
