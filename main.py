import logging
import climate
import yaml


def tethbot_main(yaml_config_path):
    with open(yaml_config_path, "r") as fid:
        client = yaml.load(fid)
        client()
    # t.run_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    climate.call(tethbot_main)
