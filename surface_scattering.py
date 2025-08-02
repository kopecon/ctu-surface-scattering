import logging

from _gui import start_gui
from _app_logger import log_this, setup_logging
import _parameters as param

# TODO: motor 3 from 90 60 30 0 270 300 330 does not graph properly  (Software)
# FIXME: Motor 3 2 1 positions display in GUI is stuck
# TODO: TEST periodical data measurement for real time graph  (Hardware)
# FIXME: Doesn't graph motor 1 at 60 degrees  (Hardware)


logger = logging.getLogger(__name__)


def main():
    setup_logging(param.logger_config_path)
    logger.info(f'{log_this.space}Lunching Surface Scattering...')

    try:
        start_gui()

    except Exception as e:
        logger.exception(f'{log_this.space}Exception occurred: {e}')
        raise Exception(f"Exception occurred: {e}")


if __name__ == '__main__':
    main()
