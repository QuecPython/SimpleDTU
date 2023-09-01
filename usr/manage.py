import _thread
import checkNet
from usr.dtu import Dtu

_thread.stack_size(4096)


def main():
    while checkNet.waitNetworkReady() == (3, 1):
        print('network not ready, waiting...')
        break

    dtu = Dtu('HuaYun')

    dtu.config.read_from_json('/usr/dtu_config.json')

    dtu.run()


if __name__ == '__main__':
    main()
