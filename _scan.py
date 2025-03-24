# System libraries
import os
import time
import warnings
from datetime import timedelta, datetime


# Data manipulation libraries
import pandas as pd


def _days_hours_minutes_seconds(dt):
    days = dt.days
    hours = dt.seconds // 3600
    minutes = (dt.seconds // 60) % 60
    seconds = dt.seconds - ((dt.seconds // 3600) * 3600) - ((dt.seconds % 3600 // 60) * 60)
    return days, hours, minutes, seconds


def _save_to_file(data, data_ratio, scan_type):
    name = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv"  # Name of the saved file
    print("Output file name:", name)

    output_path = "./DataOutput/"  # Where the file is going to be saved
    os.makedirs(output_path, exist_ok=True)

    if scan_type == '1D':
        if not os.path.exists(f"{output_path}/data_1D"):
            os.makedirs(f"{output_path}/data_1D/")
        output_path = f"{output_path}/data_1D/"
    elif scan_type == '3D':
        if not os.path.exists(f"{output_path}/data_3D"):
            os.makedirs(f"{output_path}/data_3D/")
        output_path = f"{output_path}/data_3D/"
    with open(f'{output_path}/{name}', "a") as f:
        line = "{};{};{};{};{};{}".format(
            data.iloc[0], data.iloc[1], data.iloc[2], data.iloc[3], data.iloc[4], data_ratio)
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


def _collect_sensor_data(motor_1_position, motor_2_position, motor_3_position, sensor):
    n = 0

    column_names = ["a", "b", "c", "d", "e"]
    measurement_data = pd.DataFrame(columns=column_names)

    while n < int(sensor.number_of_measurement_points):
        sensor_data = sensor.measure_scattering()
        data = {
            "a": [motor_1_position],
            "b": [motor_2_position],
            "c": [motor_3_position],
            "d": [sensor_data[0]],
            "e": [sensor_data[1]]}
        current_scan = pd.DataFrame(data)
        measurement_data = pd.concat((measurement_data, current_scan), axis=0)

        # To prevent pandas FutureWarning spam:
        warnings.simplefilter(action='ignore', category=FutureWarning)

        n += 1

    measurement_data = measurement_data.mean()
    print("m1:", measurement_data.iloc[0], " m2:", measurement_data.iloc[1], " m3:", measurement_data.iloc[2])
    print(
        "prumer Signal1:",
        measurement_data.iloc[3],
        " a prumer Signal2:",
        measurement_data.iloc[4],
    )
    data_ratio = measurement_data.iloc[3] / measurement_data.iloc[4]
    print("Pomer je:", data_ratio)

    return measurement_data, data_ratio


def scan(controller, thread_signal):

    progress_count = 0

    angles = [0, 0, 0]

    motor_1 = controller.motor_1
    motor_2 = controller.motor_2
    motor_3 = controller.motor_3
    sensor = controller.sensor

    full_range = (len(motor_1.scan_positions) * len(motor_2.scan_positions) * len(motor_3.scan_positions))

    for i in motor_1.scan_positions:
        if hasattr(motor_1, 'move_to_position'):
            motor_1.move_to_position(i)

        angles[0] = i

        for j in motor_2.scan_positions:
            if hasattr(motor_2, 'move_to_position'):
                motor_2.move_to_position(j)

            angles[1] = j

            for k in motor_3.scan_positions:
                scan_start_time = time.time()
                if hasattr(motor_3, 'move_to_position'):
                    motor_3.move_to_position(k)

                angles[2] = k

                motor_1_position = angles[0]
                motor_2_position = angles[1]
                motor_3_position = angles[2]

                measurement_data, data_ratio = _collect_sensor_data(
                    motor_1_position,
                    motor_2_position,
                    motor_3_position,
                    sensor)

                controller.measure_scattering_here()

                progress_count += 1
                _update_progressbar(progress_count, scan_start_time, full_range, thread_signal)
                _save_to_file(measurement_data, data_ratio, controller.scan_type)

    print("Done")
