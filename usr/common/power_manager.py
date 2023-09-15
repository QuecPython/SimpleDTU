"""
@File : power_manager.py
@Author : Dustin Wei
@Email : dustin.wei@quectel.com
@Date : 2023/9/14 15:24 
"""
import pm
import utime
from misc import Power
from machine import RTC


class PowerManager(object):

    def __init__(self):
        self.__rtc = RTC()
        self.__pm = pm
        self.get_vbatt = Power.getVbatt
        self.power_down = Power.powerDown
        self.power_restart = Power.powerRestart
        self.get_power_on_reason = Power.powerOnReason
        self.get_power_down_reason = Power.powerDownReason

    def set_rtc(self, seconds, callback=None):
        self.__rtc.enable_alarm(0)
        rtc_time = self.__rtc.datetime()
        rtc_time = rtc_time[:3] + rtc_time[4:7] + (0, 0)
        alarm_time = utime.localtime(utime.mktime(list(rtc_time)) + seconds)
        print('alarm_time: ', alarm_time)
        print('rtc_time: ', self.__rtc.datetime())
        def default_cb(_):
            pass
        self.__rtc.register_callback(callback or default_cb)
        self.__rtc.set_alarm(alarm_time)
        return self.__rtc.enable_alarm(1) == 0

    def set_auto_sleep(self, flag=True):
        return self.__pm.autosleep(int(flag)) == 0

    def __init_tau(self, seconds):
        if isinstance(seconds, int) and seconds > 0:
            if seconds >= (320 * 3600) and (seconds % (320 * 3600) == 0 or (0 < int(seconds / (320 * 3600)) <= 31 <= int(seconds / (10 * 3600)))):
                self.__tau_unit = 6
                self.__tau_time = int(seconds / (320 * 3600))
            elif seconds >= (10 * 3600) and (seconds % (10 * 3600) == 0 or (0 < int(seconds / (10 * 3600)) <= 31 < int(seconds / 3600))):
                self.__tau_unit = 2
                self.__tau_time = int(seconds / (10 * 3600))
            elif seconds >= 3600 and (seconds % 3600 == 0 or (0 < int(seconds / 3600) <= 31 <= int(seconds / 600))):
                self.__tau_unit = 1
                self.__tau_time = int(seconds / 3600)
            elif seconds >= 600 and (seconds % 600 == 0 or (0 < int(seconds / 600) <= 31 <= int(seconds / 60))):
                self.__tau_unit = 0
                self.__tau_time = int(seconds / 600)
            elif seconds >= 60 and (seconds % 60 == 0 or (0 < int(seconds / 60) <= 31 <= int(seconds / 30))):
                self.__tau_unit = 5
                self.__tau_time = int(seconds / 60)
            elif seconds >= 30 and (seconds % 30 == 0 or (0 < int(seconds / 30) <= 31)):
                self.__tau_unit = 4
                self.__tau_time = int(seconds / 30)
            else:
                self.__tau_unit = 3
                self.__tau_time = int(seconds / 2)

    def __init_act(self, seconds):
        if isinstance(seconds, int) and seconds > 0:
            if seconds % 600 == 0:
                self.__act_unit = 2
                self.__act_time = int(seconds / 600)
            elif seconds % 60 == 0:
                self.__act_unit = 1
                self.__act_time = int(seconds / 600)
            else:
                self.__act_unit = 0
                self.__act_time = int(seconds / 2)

    def set_psm(self, active=True, tau_seconds=None, act_seconds=None):
        if active:
            if tau_seconds is None and act_seconds is None:
                return pm.set_psm_time(1)
            self.__init_tau(tau_seconds)
            self.__init_act(act_seconds)
            return pm.set_psm_time(self.__tau_unit, self.__tau_time, self.__act_unit, self.__act_time)
        else:
            return pm.set_psm_time(0)
