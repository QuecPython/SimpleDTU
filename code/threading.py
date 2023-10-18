import utime
import usys
import _thread
import osTimer


class Lock(object):

    def __init__(self):
        self.__lock = _thread.allocate_lock()
        self.__owner = None

    def __enter__(self):
        self.acquire()

    def __exit__(self, *args, **kwargs):
        self.release()

    def acquire(self):
        flag = self.__lock.acquire()
        self.__owner = _thread.get_ident()
        return flag

    def release(self):
        self.__owner = None
        return self.__lock.release()

    def locked(self):
        return self.__lock.locked()

    @property
    def owner(self):
        return self.__owner


class Waiter(object):
    """WARNING: Waiter object can only be used once."""

    def __init__(self):
        self.__lock = Lock()
        self.__lock.acquire()
        self.__gotit = True

    @property
    def unlock_timer(self):
        timer = getattr(self, '__unlock_timer__', None)
        if timer is None:
            timer = osTimer()
            setattr(self, '__unlock_timer__', timer)
        return timer

    def __auto_release(self, _):
        if self.__release():
            self.__gotit = False
        else:
            self.__gotit = True

    def acquire(self, timeout=-1):
        """timeout <= 0 for blocking forever."""
        if not self.__lock.locked():
            raise RuntimeError('Waiter object can only be used once.')
        self.__gotit = True
        if timeout > 0:
            self.unlock_timer.start(timeout * 1000, 0, self.__auto_release)
        self.__lock.acquire()  # block here
        if timeout > 0:
            self.unlock_timer.stop()
        self.__release()
        return self.__gotit

    def __release(self):
        try:
            self.__lock.release()
        except RuntimeError:
            return False
        return True

    def release(self):
        return self.__release()


class Condition(object):

    def __init__(self, lock=None):
        if lock is None:
            lock = Lock()
        self.__lock = lock
        self.__waiters = []
        self.acquire = self.__lock.acquire
        self.release = self.__lock.release

    def __enter__(self):
        self.acquire()

    def __exit__(self, *args, **kwargs):
        self.release()

    def __is_owned(self):
        return self.__lock.locked() and self.__lock.owner == _thread.get_ident()

    def wait(self, timeout=None):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        waiter = Waiter()
        self.__waiters.append(waiter)
        self.release()
        try:
            if timeout is None:
                return waiter.acquire()
            else:
                return waiter.acquire(timeout)
        finally:
            self.acquire()
            self.__waiters.remove(waiter)

    def wait_for(self, predicate, timeout=None):
        endtime = None
        remaining = timeout
        result = predicate()
        while not result:
            if remaining is not None:
                if endtime is None:
                    endtime = utime.time() + remaining
                else:
                    remaining = endtime - utime.time()
                    if remaining <= 0.0:
                        break
            self.wait(remaining)
            result = predicate()
        return result

    def notify(self, n=1):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        if n <= 0:
            raise ValueError('invalid param, n should be > 0.')
        for waiter in self.__waiters[:n]:
            waiter.release()

    def notify_all(self):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        for waiter in self.__waiters:
            waiter.release()


class Event(object):

    def __init__(self):
        self.__flag = False
        self.__cond = Condition()

    def wait(self, timeout=None):
        with self.__cond:
            return self.__cond.wait_for(lambda: self.__flag, timeout=timeout)

    def set(self):
        with self.__cond:
            self.__flag = True
            self.__cond.notify_all()

    def clear(self):
        with self.__cond:
            self.__flag = False

    def is_set(self):
        with self.__cond:
            return self.__flag


class Queue(object):

    class Full(Exception):
        pass

    class Empty(Exception):
        pass

    def __init__(self, max_size=100):
        self.__deque = []
        self.__max_size = max_size
        self.__lock = Lock()
        self.__not_empty = Condition(self.__lock)
        self.__not_full = Condition(self.__lock)

    def put(self, item, block=True, timeout=None):
        with self.__not_full:
            if not block:
                if len(self.__deque) >= self.__max_size:
                    raise self.Full
            elif timeout is not None and timeout <= 0:
                raise ValueError("'timeout' must be a positive number.")
            else:
                if not self.__not_full.wait_for(lambda: len(self.__deque) < self.__max_size, timeout=timeout):
                    raise self.Full
            self.__deque.append(item)
            self.__not_empty.notify()

    def get(self, block=True, timeout=None):
        with self.__not_empty:
            if not block:
                if len(self.__deque) == 0:
                    raise self.Empty
            elif timeout is not None and timeout <= 0:
                raise ValueError("'timeout' must be a positive number.")
            else:
                if not self.__not_empty.wait_for(lambda: len(self.__deque) != 0, timeout=timeout):
                    raise self.Empty
            item = self.__deque.pop(0)
            self.__not_full.notify()
            return item

    def size(self):
        with self.__lock:
            return len(self.__deque)

    def clear(self):
        with self.__lock:
            self.__deque.clear()


class _Result(object):

    class TimeoutError(Exception):
        pass

    def __init__(self):
        self.__rv = None
        self.__exc = None
        self.__finished = Event()

    def set(self, exc, rv):
        self.__exc = exc
        self.__rv = rv
        self.__finished.set()

    def get(self, timeout=None):
        if self.__finished.wait(timeout=timeout):
            if self.__exc:
                raise self.__exc
            return self.__rv
        else:
            raise self.TimeoutError('get result timeout.')


class Thread(object):

    def __init__(self, target=None, args=(), kwargs=None):
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs or {}
        self.__ident = None

    def __repr__(self):
        return '<Thread {}>'.format(self.__ident)

    def is_running(self):
        if self.__ident is None:
            return False
        else:
            return _thread.threadIsRunning(self.__ident)

    def start(self, delay=-1):
        if not self.is_running():
            result = _Result()
            self.__ident = _thread.start_new_thread(self.run, (result, delay))
            return result

    def stop(self):
        if self.is_running():
            _thread.stop_thread(self.__ident)
            self.__ident = None

    def run(self, result, delay):
        if delay > 0:
            utime.sleep(delay)
        try:
            rv = self.__target(*self.__args, **self.__kwargs)
        except Exception as e:
            result.set(e, None)
        else:
            result.set(None, rv)

    @property
    def ident(self):
        return self.__ident

    @classmethod
    def get_current_thread_ident(cls):
        return _thread.get_ident()


class _WorkItem(object):

    def __init__(self, fn, args, kwargs):
        self.__fn = fn
        self.__args = args
        self.__kwargs = kwargs
        self.result = _Result()

    def run(self):
        try:
            rv = self.__fn(*self.__args, **self.__kwargs)
        except Exception as e:
            self.result.set(e, None)
        else:
            self.result.set(rv, None)


def _worker(work_queue):
    while True:
        try:
            item = work_queue.get()
            item.run()
        except Exception as e:
            usys.print_exception(e)


class ThreadPoolExecutor(object):

    def __init__(self, max_workers=4):
        if max_workers <= 0:
            raise ValueError('max_workers must be greater than 0.')
        self.__max_workers = max_workers
        self.__work_queue = Queue()
        self.__threads = set()
        self.__lock = Lock()

    def submit(self, fn, *args, **kwargs):
        item = _WorkItem(fn, args, kwargs)
        self.__work_queue.put(item)
        self.__adjust_thread_count()
        return item.result

    def __adjust_thread_count(self):
        with self.__lock:
            if len(self.__threads) < self.__max_workers:
                t = Thread(target=_worker, args=(self.__work_queue,))
                t.start()
                self.__threads.add(t)

    def shutdown(self):
        with self.__lock:
            for t in self.__threads:
                t.stop()
            self.__threads.clear()
