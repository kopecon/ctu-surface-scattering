# System libraries
import os
import time

from datetime import timedelta, datetime


def _days_hours_minutes_seconds(dt):
    days = dt.days
    hours = dt.seconds // 3600
    minutes = (dt.seconds // 60) % 60
    seconds = dt.seconds - ((dt.seconds // 3600) * 3600) - ((dt.seconds % 3600 // 60) * 60)
    return days, hours, minutes, seconds


def _save_to_file(data, scan_type, name):

    output_path = "./DataOutput/"  # Where the file is going to be saved
    os.makedirs(output_path, exist_ok=True)
    # Create the directories:
    if scan_type == '1D':
        if not os.path.exists(f"{output_path}/data_1D"):
            os.makedirs(f"{output_path}/data_1D/")
        output_path = f"{output_path}/data_1D/"
    elif scan_type == '3D':
        if not os.path.exists(f"{output_path}/data_3D"):
            os.makedirs(f"{output_path}/data_3D/")
        output_path = f"{output_path}/data_3D/"

    # Write into file:
    with open(f'{output_path}/{name}', "a") as f:
        line = "{};{};{};{};{};{}".format(
            data.iloc[0], data.iloc[1], data.iloc[2], data.iloc[3], data.iloc[4], data.iloc[5], 3)
        print(line, file=f)


def _update_progressbar(progress_count, start_time, full_range, thread_signal):
    print("Progres count: ", progress_count)
    progress = (100 / full_range) * progress_count
    print("Progress: ", progress, " %")

    stop_time = time.time()
    dt = stop_time - start_time
    remaining_positions = full_range - progress_count
    time_to_finish = dt * remaining_positions
    time_to_finish = (time_to_finish / 20) + time_to_finish  # +20% na prejezdy M1 a M2
    print("Remaining positions = ", remaining_positions)
    delta = timedelta(seconds=time_to_finish)
    (days, hours, minutes, seconds) = _days_hours_minutes_seconds(delta)
    print("Time to finish: ", days, "d", hours, "h", minutes, "m", seconds, "s")
    output_signal = [progress, time_to_finish]
    if hasattr(thread_signal, 'emit'):
        thread_signal.emit(output_signal)


def scan(controller, thread_signal):
    name = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv"  # Name of the saved file
    print("Output file name:", name)

    progress_count = 0

    motor_1 = controller.motor_1
    motor_2 = controller.motor_2
    motor_3 = controller.motor_3

    full_range = (len(motor_1.scan_positions) * len(motor_2.scan_positions) * len(motor_3.scan_positions))

    for i in motor_1.scan_positions:
        stop_check = motor_1.move_to_position(i)
        if stop_check == 1:
            # Motor was called to stop => end scanning
            return controller.unstop_motors()

        for j in motor_2.scan_positions:
            stop_check = motor_2.move_to_position(j)
            if stop_check == 1:
                # Motor was called to stop => end scanning
                return controller.unstop_motors()

            for k in motor_3.scan_positions:
                scan_start_time = time.time()
                stop_check = motor_3.move_to_position(k)
                if stop_check == 1:
                    # Motor was called to stop => end scanning
                    return controller.unstop_motors()

                # TODO: clean measuring etc...
                measurement_data = controller.collect_sensor_data()

                progress_count += 1
                _update_progressbar(progress_count, scan_start_time, full_range, thread_signal)
                _save_to_file(measurement_data, controller.scan_type, name)

    print("Done")
