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


def _find_range_double(step):
    start1 = 270
    stop1 = 360
    start2 = 0
    stop2 = 90
    dx1 = int((stop1 - start1) / step)
    dx2 = int((stop2 - start2) / step)
    point1 = np.linspace(start1, stop1, endpoint=True, num=dx1 + 1)
    point2 = np.linspace(start2, stop2, endpoint=True, num=dx2 + 1)
    point0 = np.concatenate((point1, point2))
    point = np.delete(point0, np.where(point0 == 360))
    return point


def _days_hours_minutes_seconds(dt):
    return (
        dt.days,  # days
        dt.seconds // 3600,  # hours
        (dt.seconds // 60) % 60,  # minutes
        dt.seconds
        - ((dt.seconds // 3600) * 3600)
        - ((dt.seconds % 3600 // 60) * 60)  # seconds
    )


def _conduct_measurement(number_of_measurement_points, motor_1_position, motor_2_position, motor_3_position):
    try:
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
    except:
        # TODO: Why do we need exception, specify. Once Task() ran, Try block not necessary ... why?
        print("Passed exception")


def _save_file(name, data, data_ratio):
    with open(name, "a") as f:
        line = "{};{};{};{};{};{}".format(data.iloc[0],
                                          data.iloc[1],
                                          data.iloc[2],
                                          data.iloc[3],
                                          data.iloc[4],
                                          data_ratio)
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
    print("Time to finish = ", time_to_finish)
    delta = timedelta(seconds=time_to_finish)
    (days, hours, minutes, seconds) = _days_hours_minutes_seconds(delta)
    print("Time to finish: ", days, "d", hours, "h", minutes, "m", seconds, "s")
    output_signal = [progress, time_to_finish]
    thread_signal.emit(output_signal)  # vyslani signalu


def scan_1d(motors, input_data, thread_signal):
    input_data = [input_data[0], input_data[0], input_data[2], input_data[3], input_data[3], input_data[5], 270, 90, input_data[8], input_data[9], input_data[10]]
    scan_3d(motors, input_data, thread_signal)


def scan_3d(motors, input_data, thread_signal):
    motor_1 = motors[1]
    motor_2 = motors[2]
    motor_3 = motors[3]
    progress_count = 0

    print("3D measurement in progress...")

    angles = [0, 0, 0]

    name = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv"
    print("Writing", name)

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
    print("Motor 3 range:", motor_3_range)

    # Temporary solution:
    if input_data[10]:
        first_half = _find_range(270, 360, motor_3_step)
        second_half = _find_range(0, 90, motor_3_step)
        motor_3_range = np.concatenate((first_half, second_half), axis=0)
        motor_3_range = np.delete(motor_3_range, np.where(motor_3_range == 0))

    full_range = (len(motor_1_range) * len(motor_2_range) * len(motor_3_range))

    number_of_measurement_points = input_data[9]

    for i in motor_1_range:
        motor_1.move_to_position(i)

        angles[0] = i

        for j in motor_2_range:
            motor_2.move_to_position(j)

            angles[1] = j

            for k in motor_3_range:
                scan_start_time = time.time()
                motor_3.move_to_position(k)

                angles[2] = k

                motor_1_position = angles[0]
                motor_2_position = angles[1]
                motor_3_position = angles[2]

                if _conduct_measurement(number_of_measurement_points, motor_1_position, motor_2_position, motor_3_position) is not None:
                    measurement_data, data_ratio = _conduct_measurement(
                    number_of_measurement_points, motor_1_position, motor_2_position, motor_3_position)

                    progress_count += 1
                    _update_progressbar(progress_count, scan_start_time, full_range, thread_signal)

                    _save_file(name, measurement_data, data_ratio)

    print("Done")
