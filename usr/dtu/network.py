import uos
import sim
import checkNet
import dataCall
from usr.dtu.logging import getLogger


logger = getLogger(__name__)


class NetMonitor(object):

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
                if sim.setCallback(cls.__sim_switch_callback) != 0:
                    logger.warn('register sim switch callback failed.')
        except Exception as e:
            logger.error('sim check init failed: {}'.format(e))

    @staticmethod
    def __sim_switch_callback(state):
        if state == 1:
            logger.info('SIM card insertion')
        elif state == 2:
            logger.info('SIM card removal')
        else:
            logger.info('unknow sim state')

    @classmethod
    def __net_check_init(cls):
        try:
            if dataCall.setCallback(cls.__net_callback) != 0:
                logger.info('register data callback failed.')
        except Exception as e:
            logger.error('net check init failed: {}'.format(e))

    @staticmethod
    def __net_callback(args):
        pdp, state = args[0], args[1]
        if state == 0:
            logger.info('network disconnected, PDP ID: {}'.format(pdp))
        elif state == 1:
            logger.info('network connected, PDP ID: {}'.format(pdp))

    @classmethod
    def wait_network_ready(cls):
        while True:
            code = checkNet.waitNetworkReady()
            if code == (3, 1):
                logger.info('net work ready.')
                break
            logger.warn('network not ready, code: {}. continue waiting...'.format(code))
