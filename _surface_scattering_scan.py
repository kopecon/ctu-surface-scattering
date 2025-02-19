import os

import pandas as pd
from datetime import timedelta
import nidaqmx
from nidaqmx.constants import Edge
from nidaqmx.constants import AcquisitionType
import numpy as np
import time
from datetime import datetime

import warnings


# NI-DAQmx 2025 Q1 has to be installed on the executing pc to run the scan.
# NI-DAQmx 2025 Q1 download: https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html?srsltid=AfmBOooJ-Ko5HpJHEr4yPzQEZKufBWdBc1JjWhomtdJ27QKXivgjvTBr#559060
# TODO: Change saving file management
# TODO: Test functionality

def _find_range(start, stop, step):
    dx = int(abs((stop - start)) / step + 1)
    return np.linspace(start, stop, endpoint=True, num=dx)


def _days_hours_minutes_seconds(dt):
    days = dt.days
    hours = dt.seconds // 3600
    minutes = (dt.seconds // 60) % 60
    seconds = dt.seconds - ((dt.seconds // 3600) * 3600) - ((dt.seconds % 3600 // 60) * 60)
    return days, hours, minutes, seconds


def _conduct_measurement(number_of_measurement_points, motor_1_position, motor_2_position, motor_3_position):
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(
            "myDAQ1/ai0:1"
        )
        task.timing.cfg_samp_clk_timing(
            100000,
            source="",
            active_edge=Edge.RISING,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=10,
        )

        n = 0

        column_names = ["a", "b", "c", "d", "e"]
        measurement_data = pd.DataFrame(columns=column_names)

        while n < int(number_of_measurement_points):
            sensor_data = task.read()
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


def _save_file(name, data, data_ratio, scan_type):
    output_path = "./DataOutput/"
    os.makedirs(output_path, exist_ok=True)

    if scan_type == '1D':
        if not os.path.exists(f"{output_path}/data_1D"):
            os.makedirs(f"{output_path}/data_1D/")
        output_path = f"{output_path}/data_1D/"
    elif scan_type == '3D':
        if not os.path.exists(f"{output_path}/data_3D"):
            os.makedirs(f"{output_path}/data_3D/")
        output_path = f"{output_path}/data_3D/"
    print(scan_type)
    print(output_path)
    with open(f'{output_path}/{name}', "a") as f:
        line = "{};{};{};{};{};{}".format(data.iloc[0], data.iloc[1], data.iloc[2], data.iloc[3], data.iloc[4], data_ratio)
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


def scan(motors, input_data, thread_signal):
    print("3D measurement in progress...")

    progress_count = 0

    angles = [0, 0, 0]

    if input_data[10]:
        scan_type = '1D'
    else:
        scan_type = '3D'

    motor_1 = motors[1]
    motor_2 = motors[2]
    motor_3 = motors[3]

    name = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv"
    print("Output file name:", name)

    motor_1_from = float(input_data[0])
    motor_1_to = float(input_data[1])
    motor_1_step = float(input_data[2])
    motor_1_range = _find_range(motor_1_from, motor_1_to, motor_1_step)

    motor_2_from = float(input_data[3])
    motor_2_to = float(input_data[4])
    motor_2_step = float(input_data[5])
    motor_2_range = _find_range(motor_2_from, motor_2_to, motor_2_step)

    motor_3_from = float(input_data[6])
    motor_3_to = float(input_data[7])
    motor_3_step = float(input_data[8])
    motor_3_range = _find_range(motor_3_from, motor_3_to, motor_3_step)

    # Finding range for motor 3
    if scan_type == '1D':
        first_half = _find_range(270, 360, motor_3_step)
        second_half = _find_range(0, 90, motor_3_step)
        motor_3_range = np.concatenate((first_half, second_half), axis=0)
        motor_3_range = np.delete(motor_3_range, np.where(motor_3_range == 0))

    full_range = (len(motor_1_range) * len(motor_2_range) * len(motor_3_range))

    number_of_measurement_points = input_data[9]

    for i in motor_1_range:
        if hasattr(motor_1, 'move_to_position'):
            motor_1.move_to_position(i)

        angles[0] = i

        for j in motor_2_range:
            if hasattr(motor_2, 'move_to_position'):
                motor_2.move_to_position(j)

            angles[1] = j

            for k in motor_3_range:
                scan_start_time = time.time()
                if hasattr(motor_3, 'move_to_position'):
                    motor_3.move_to_position(k)

                angles[2] = k

                motor_1_position = angles[0]
                motor_2_position = angles[1]
                motor_3_position = angles[2]

                measurement_data, data_ratio = _conduct_measurement(
                    number_of_measurement_points, motor_1_position, motor_2_position, motor_3_position)

                progress_count += 1
                _update_progressbar(progress_count, scan_start_time, full_range, thread_signal)

                _save_file(name, measurement_data, data_ratio, scan_type)

    print("Done")


if __name__ == '__main__':
    # Fake data for scan testing
    scan([None, None, None, None], input_data=[0, 180, 30, 0, 180, 30, 0, 180, 30, 5, True], thread_signal=1)
