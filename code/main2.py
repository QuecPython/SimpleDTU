from usr.dtu import DTU
from usr import network


dtu = DTU('Quectel')
dtu.config.read_from_json('/usr/dtu_config.json')


if __name__ == '__main__':
    # 网络就绪
    network.wait_network_ready()
    # dtu应用
    dtu.run()
