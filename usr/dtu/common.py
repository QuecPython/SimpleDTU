import utime
import _thread
import osTimer
from queue import Queue as uQueue


Lock = _thread.allocate_lock


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


class Waiter(object):

    def __init__(self):
        self.__lock = _thread.allocate_lock()
        self.__lock.acquire()
        self.__unlock_timer = osTimer()

    def __auto_unlock(self, _):
        self.notify()

    def wait(self, timeout=-1):
        if timeout > 0:
            self.__unlock_timer.start(timeout * 1000, 0, self.__auto_unlock)
        self.__lock.acquire()  # block until timeout or notify
        self.__lock.release()
        self.__unlock_timer.stop()

    def notify(self):
        if self.__lock.locked():
            self.__lock.release()


class Condition(object):

    def __init__(self):
        self.__lock = _thread.allocate_lock()
        self.__waiters = []

    def wait(self, timeout=-1):
        waiter = Waiter()
        with self.__lock:
            self.__waiters.append(waiter)
        waiter.wait(timeout)  # block until timeout or notify
        with self.__lock:
            self.__waiters.remove(waiter)

    def notify(self, n=1):
        if n <= 0:
            raise ValueError('invalid param, n should be > 0.')
        with self.__lock:
            for waiter in self.__waiters[:n]:
                waiter.notify()

    def notify_all(self):
        with self.__lock:
            for waiter in self.__waiters:
                waiter.notify()


class Event(object):

    def __init__(self):
        self.__lock = _thread.allocate_lock()
        self.flag = False
        self.cond = Condition()

    def wait(self):
        """wait until internal flag is True"""
        if not self.flag:
            self.cond.wait()
        return self.flag

    def set(self):
        with self.__lock:
            self.flag = True
            self.cond.notify_all()

    def clear(self):
        with self.__lock:
            self.flag = False

    def is_set(self):
        with self.__lock:
            return self.flag


class WaitTimeout(Exception):
    pass


class Result(object):

    def __init__(self):
        self.__rv = None
        self.__exc = None
        self.__finished = False
        self.__cond = Condition()

    def set(self, exc, rv):
        self.__exc = exc
        self.__rv = rv
        self.__finished = True
        self.__cond.notify_all()

    def get(self, timeout=-1):
        self.__cond.wait(timeout=timeout)
        if not self.__finished:
            raise WaitTimeout
        if self.__exc:
            raise self.__exc
        return self.__rv


class Thread(object):

    def __init__(self, target=None, args=(), kwargs=None):
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs or {}
        self.__worker_thread_id = None
        self.__lock = Lock()

    def __repr__(self):
        return '<Thread {}>'.format(self.__worker_thread_id)

    def is_running(self):
        return self.__worker_thread_id and _thread.threadIsRunning(self.__worker_thread_id)

    def start(self, delay=-1):
        if not self.is_running():
            if delay > 0:
                utime.sleep(delay)
            result = Result()
            self.__worker_thread_id = _thread.start_new_thread(self.run, (result, ))
            return result

    def stop(self):
        if self.is_running():
            _thread.stop_thread(self.__worker_thread_id)
            self.__worker_thread_id = None

    def run(self, result):
        try:
            rv = self.__target(*self.__args, **self.__kwargs)
        except Exception as e:
            result.set(e, None)
        else:
            result.set(None, rv)


class Queue(object):
    def __init__(self, maxsize=100):
        self.__queue = uQueue(maxsize=maxsize)
        self.__timer = osTimer()
        self.__timer_lock = _thread.allocate_lock()

    def put(self, data):
        self.__queue.put(data)

    def get(self, timeout=-1):
        if timeout > 0:
            with self.__timer_lock:
                self.__timer.start(timeout * 1000, 0, lambda args: self.put(None))
                rv = self.__queue.get()
                self.__timer.stop()
        elif timeout == 0:
            rv = None if self.__queue.empty() else self.__queue.get()
        else:
            rv = self.__queue.get()
        return rv
