import _thread
from usr.dtu import Dtu


# for 800E
_thread.stack_size(4096)


def main():
    # start dtu service
    dtu = Dtu('HuaYun')
    dtu.config.read_from_json('/usr/dtu_config.json')
    dtu.run()


if __name__ == '__main__':
    main()
