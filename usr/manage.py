import _thread
from usr.dtu import Dtu
from usr.dtu.network import NetMonitor


# for 800E
_thread.stack_size(4096)


def main():
    # wait network ready
    NetMonitor.init()
    NetMonitor.wait_network_ready()

    # start dtu service
    dtu = Dtu('HuaYun')
    dtu.config.read_from_json('/usr/dtu_config.json')
    dtu.run()


if __name__ == '__main__':
    main()
