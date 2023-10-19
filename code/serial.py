from machine import UART
from usr.threading import Condition, Lock


class Serial(object):

    class TimeoutError(Exception):
        pass

    def __init__(self, port=2, baudrate=115200, bytesize=8, parity=0, stopbits=1, flowctl=0, rs485_config=None):
        self.__port = port
        self.__baudrate = baudrate
        self.__bytesize = bytesize
        self.__parity = parity
        self.__stopbits = stopbits
        self.__flowctl = flowctl
        self.__rs485_config = rs485_config
        self.__uart = None
        self.__r_cond = Condition()
        self.__w_cond = Lock()

    def __repr__(self):
        return '<UART{},{},{},{},{},{},{}>'.format(
            self.__port, self.__baudrate, self.__bytesize,
            self.__parity, self.__stopbits, self.__flowctl,
            self.__rs485_config
        )

    @property
    def uart(self):
        if self.__uart is None:
            raise TypeError('uart not open.')
        return self.__uart

    def open(self):
        self.__uart = UART(
            getattr(UART, 'UART{}'.format(self.__port)),
            self.__baudrate,
            self.__bytesize,
            self.__parity,
            self.__stopbits,
            self.__flowctl
        )
        if isinstance(self.__rs485_config, dict):
            gpio_num = getattr(UART, "GPIO{}".format(self.__rs485_config['gpio_num']))
            direction = self.__rs485_config['direction']
            self.__uart.control_485(gpio_num, direction)

        self.__uart.set_callback(self.__uart_cb)

    def close(self):
        self.__uart.close()
        self.__uart = None

    def __uart_cb(self, _):
        with self.__r_cond:
            self.__r_cond.notify_all()

    def write(self, data):
        with self.__w_cond:
            return self.uart.write(data)

    def read(self, size, timeout=None):
        with self.__r_cond:
            if self.__r_cond.wait_for(lambda: self.uart.any() != 0, timeout=timeout):
                return self.uart.read(min(size, self.uart.any()))
            else:
                raise self.TimeoutError('serial read timeout.')
