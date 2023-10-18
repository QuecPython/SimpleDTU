from usr.dtu import DTU


dtu = DTU('Quectel')
dtu.config.read_from_json('/usr/dtu_config.json')


if __name__ == '__main__':
    dtu.run()
