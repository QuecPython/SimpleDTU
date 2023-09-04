from machine import UART, Timer
from usr.dtu.common import Condition, Lock


class Serial(object):
    r_lock = Lock()
    w_lock = Lock()

    def __init__(self, port=2, baudrate=115200, bytesize=8, parity=0, stopbits=1, flowctl=0, rs485_pin=None):
        self.__port = port
        self.__baudrate = baudrate
        self.__bytesize = bytesize
        self.__parity = parity
        self.__stopbits = stopbits
        self.__flowctl = flowctl
        self.__rs485_pin = rs485_pin

        self.__uart = None
        self.__cond = Condition()

    def __str__(self):
        return '<UART{},{},{},{},{},{},{}>'.format(
            self.__port, self.__baudrate, self.__bytesize,
            self.__parity, self.__stopbits, self.__flowctl,
            self.__rs485_pin
        )

    def init(self):
        self.__uart = UART(
            getattr(UART, 'UART{}'.format(self.__port)),
            self.__baudrate,
            self.__bytesize,
            self.__parity,
            self.__stopbits,
            self.__flowctl
        )
        if self.__rs485_pin is not None:
            rs485_pin = getattr(UART, "GPIO{}".format(self.__rs485_pin))
            self.__uart.control_485(rs485_pin, 1)

        self.__uart.set_callback(self.__uart_cb)

    def __uart_cb(self, args):
        self.__cond.notify()

    def write(self, data):
        with self.w_lock:
            self.__uart.write(data)

    def read(self, size, timeout=-1):
        with self.r_lock:
            if self.__uart.any() == 0 and timeout != 0:
                self.__cond.wait(timeout=timeout)
            data = self.__uart.read(min(size, self.__uart.any()))
            return data
