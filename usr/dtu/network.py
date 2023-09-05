import uos
import sim
import checkNet
import dataCall
from usr.dtu.common import PubSub
from usr.dtu.logging import getLogger


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
        while True:
            code = checkNet.waitNetworkReady()
            if code == (3, 1):
                logger.info('net work ready.')
                break
            logger.warn('network not ready, code: {}. continue waiting...'.format(code))
