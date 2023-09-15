import uos
import sim
import net
import utime
import checkNet
import dataCall
from misc import Power
from usr.common.pubsub import PubSub
from usr.common.logging import getLogger


logger = getLogger(__name__)


class NetMonitor(object):
    SIM_STATUS_TOPIC = '/sim/status'
    NET_STATUS_TOPIC = '/net/status'

    @classmethod
    def init(cls):
        logger.info('init net monitor. system information: {}'.format(uos.uname()))
        cls.__sim_check_init()
        cls.__net_check_init()

    @classmethod
    def __sim_check_init(cls):
        try:
            trigger_level = 1
            if sim.setSimDet(1, trigger_level) != 0:
                logger.info('active sim switch failed.')
            else:
                if sim.setCallback(
                        lambda state: PubSub.publish(cls.SIM_STATUS_TOPIC, state)
                ) != 0:
                    logger.warn('register sim switch callback failed.')
        except Exception as e:
            logger.error('sim check init failed: {}'.format(e))

    @classmethod
    def __net_check_init(cls):
        try:
            if dataCall.setCallback(
                    lambda args: PubSub.publish(cls.NET_STATUS_TOPIC, args)
            ) != 0:
                logger.info('register data callback failed.')
        except Exception as e:
            logger.error('net check init failed: {}'.format(e))

    @classmethod
    def wait_network_ready(cls):
        total = 0
        while True:
            code = checkNet.waitNetworkReady(30)
            if code == (3, 1):
                logger.info('network ready.')
                break
            logger.warn('network not ready, code: {}. continue waiting...'.format(code))
            total += 1
            if 3 <= total < 6:
                logger.info('make cfun swtich.')
                cls.cfun_switch()
            if total >= 6:
                logger.info('power restart.')
                Power.powerRestart()

    @classmethod
    def cfun_switch(cls):
        net.setModemFun(0, 0)
        utime.sleep_ms(200)
        net.setModemFun(1, 0)
