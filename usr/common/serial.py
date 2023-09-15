"""
@File : serial.py
@Author : Dustin Wei
@Email : dustin.wei@quectel.com
@Date : 2023/9/14 10:54 
"""
import utime
from machine import UART
from usr.common.threading import Condition, Lock


class Serial(object):

    class TimeoutError(Exception):
        pass

    def __init__(self, port=2, baudrate=115200, bytesize=8, parity=0, stopbits=1, flowctl=0, rs485_pin=None):
        self.__port = port
        self.__baudrate = baudrate
        self.__bytesize = bytesize
        self.__parity = parity
        self.__stopbits = stopbits
        self.__flowctl = flowctl
        self.__rs485_pin = rs485_pin

        self.__uart = None
        self.__r_cond = Condition()
        self.__w_cond = Lock()
        self.__init()

    def __repr__(self):
        return '<UART{},{},{},{},{},{},{}>'.format(
            self.__port, self.__baudrate, self.__bytesize,
            self.__parity, self.__stopbits, self.__flowctl,
            self.__rs485_pin
        )

    def __init(self):
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
        with self.__r_cond:
            self.__r_cond.notify()

    def write(self, data):
        with self.__w_cond:
            self.__uart.write(data)

    def read(self, size, timeout=None):
        with self.__r_cond:
            if timeout is None:
                while self.__uart.any() == 0:
                    self.__r_cond.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = utime.time() + timeout
                while self.__uart.any() == 0:
                    remaining = endtime - utime.time()
                    if remaining <= 0.0:
                        raise self.TimeoutError('serial read timeout.')
                    self.__r_cond.wait(remaining)
            data = self.__uart.read(min(size, self.__uart.any()))
            return data
