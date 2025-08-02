import logging
from _app_logger import log_this


logger = logging.getLogger(__name__)


def calibration(controller):
    logger.info(f'{log_this.space}Calibration started.')
    motor_1 = controller.motor_1
    motor_2 = controller.motor_2
    motor_3 = controller.motor_3

    motor_1.move_to_position(motor_1.scan_from)
    motor_2.move_to_position(motor_2.scan_from)
    motor_3.move_to_position(motor_3.scan_from)
    logger.info(f'{log_this.space}Motors in position.')

    for step in motor_3.scan_positions:
        motor_3.move_to_position(step)
        controller.collect_sensor_data()
    logger.info(f'{log_this.space}Calibration finished.')
