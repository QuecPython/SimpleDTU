import sim
import net
import utime
import checkNet
import dataCall
import sys_bus
from misc import Power
from usr.logging import getLogger


logger = getLogger(__name__)


SIM_STATUS_TOPIC = '/sim/status'
NET_STATUS_TOPIC = '/net/status'


def active_sim_hot_swap():
    try:
        trigger_level = 0
        if sim.setSimDet(1, trigger_level) != 0:
            logger.info('active sim switch failed.')
        else:
            if sim.setCallback(
                lambda state: sys_bus.publish(SIM_STATUS_TOPIC, state)
            ) != 0:
                logger.warn('register sim switch callback failed.')
    except Exception as e:
        logger.error('sim check init failed: {}'.format(e))


def active_net_callback():
    try:
        if dataCall.setCallback(
            lambda args: sys_bus.publish(NET_STATUS_TOPIC, args)
        ) != 0:
            logger.info('register data callback failed.')
    except Exception as e:
        logger.error('net check init failed: {}'.format(e))


def cfun_switch():
    net.setModemFun(0, 0)
    utime.sleep_ms(200)
    net.setModemFun(1, 0)


def wait_network_ready():
    total = 0
    while True:
        logger.info('check network ready...')
        code = checkNet.waitNetworkReady(30)
        if code == (3, 1):
            logger.info('network has been ready.')
            break
        else:
            logger.warn('network not ready, code: {}'.format(code))
            if 3 <= total < 6:
                logger.warn('make cfun switch.')
                cfun_switch()
            if total >= 6:
                logger.warn('power restart.')
                Power.powerRestart()
        total += 1


active_sim_hot_swap()
active_net_callback()
