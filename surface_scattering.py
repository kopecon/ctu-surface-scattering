"""
The surface scattering measuring project consists of 3 files:

    surface_scattering_gui.py: The main file that is meant to be executed. Builds a GUI to interact with the lab
        measurement device.

    surface_scattering_backend.py: Provides access and control of the hardware.

    surface_scattering_scan.py: Provides the scan calculations and output file storing

Hardware:
    Controller:
        BSC203 - Three-Channel Benchtop Stepper Motor Controller
        Link - https://www.thorlabs.com/thorproduct.cfm?partnumber=BSC203
    Motors:
        HDR50 - Heavy-Duty Rotation Stage with Stepper Motor
        Link - https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=1064

Dependent Software:
    "Thorlabs Kinesis" needs to be installed on the device which is to be executing this python script.
    Correct motors have to be set up in the Thorlabs Kinesis user interface.
    Kinesis user interface has to be closed while this program is running, or the controller fails to connect.
"""


import logging

from modules.gui import start_gui
from modules.app_logger import log_this, setup_logging
from modules import parameters as param

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
