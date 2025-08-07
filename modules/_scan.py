# System libraries
import time
import logging

from datetime import timedelta, datetime

import modules.parameters as param
from modules.app_logger import log_this
from utils.time_format_processing import days_hours_minutes_seconds

logger = logging.getLogger(__name__)


def _save_to_file(data, scan_type, name):

    param.output_path.mkdir(exist_ok=True)

    # Create the directories:
    if scan_type == '1D':
        param.output_path_1d.mkdir(exist_ok=True)
        current_output_path = param.output_path_1d
    else:  # Assuming its 3D scan
        param.output_path_3d.mkdir(exist_ok=True)
        current_output_path = param.output_path_3d

    # Write into file:
    with open(f'{current_output_path}/{name}', "a") as f:
        line = "{};{};{};{};{};{}".format(
            data.iloc[0], data.iloc[1], data.iloc[2], data.iloc[3], data.iloc[4], data.iloc[5], 3)
        print(line, file=f)


def _update_progressbar(progress_count, start_time, full_range, thread_signal_progress_status):
    logger.info(f"{log_this.space}Progres count: {progress_count}")
    progress = (100 / full_range) * progress_count
    logger.info(f"{log_this.space}Progress: {progress}")

    stop_time = time.time()
    dt = stop_time - start_time
    remaining_positions = full_range - progress_count
    time_to_finish = dt * remaining_positions
    time_to_finish = (time_to_finish / 20) + time_to_finish  # +20% na prejezdy M1 a M2
    logger.info(f"{log_this.space}Remaining positions = {remaining_positions}")
    delta = timedelta(seconds=time_to_finish)
    (days, hours, minutes, seconds) = days_hours_minutes_seconds(delta)
    logger.info(f"{log_this.space}Time to finish: {days}, \"d\", {hours}, \"h\", {minutes}, \"m\", {seconds}, \"s\"")
    progress_status = [progress, time_to_finish]
    if hasattr(thread_signal_progress_status, 'emit'):
        thread_signal_progress_status.emit(progress_status)


def start_scanning(controller, thread_signal_progress_status):
    name = str(datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv")  # Name of the saved file
    logger.info(f"{log_this.space}Output file name: {name}")

    progress_count = 0

    motor_1 = controller.motor_1
    motor_2 = controller.motor_2
    motor_3 = controller.motor_3

    full_range = (len(motor_1.scan_positions) * len(motor_2.scan_positions) * len(motor_3.scan_positions))

    for i in motor_1.scan_positions:
        stop_check = motor_1.move_to_position(i)
        if stop_check == 1:
            # Motor was called to stop => end scanning
            return logger.info(f"{log_this.space}Motors are stopped. Aborting...")

        for j in motor_2.scan_positions:
            stop_check = motor_2.move_to_position(j)
            if stop_check == 1:
                # Motor was called to stop => end scanning
                return logger.info(f"{log_this.space}Motors are stopped. Aborting...")

            for k in motor_3.scan_positions:
                scan_start_time = time.time()
                stop_check = motor_3.move_to_position(k)
                if stop_check == 1:
                    # Motor was called to stop => end scanning
                    return logger.info(f"{log_this.space}Motors are stopped. Aborting...")

                measurement_data = controller.collect_sensor_data()

                progress_count += 1
                _update_progressbar(progress_count, scan_start_time, full_range, thread_signal_progress_status)
                _save_to_file(measurement_data, controller.scan_type, name)

    logger.info(f"{log_this.space}Scanning done")
