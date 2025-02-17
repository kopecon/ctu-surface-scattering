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
# TODO: Specify exceptions


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


def scan_1d(motors, input_data, on_progress, on_progress2):
    motor_1 = motors[1]
    motor_2 = motors[2]
    motor_3 = motors[3]
    progress_count = 0
    print("1D measurement in progress...")
    # _____________________________________Cycle___________________________________
    angles = [0, 0, 0]

    name = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv"
    print("Writing", name)

    m1_from = float(input_data[0])
    s1 = 1

    m2_from = float(input_data[3])
    s2 = 1

    m3_step = float(input_data[8])

    maximum = (len(_find_range(m1_from, m1_from, s1))
               * len(_find_range(m2_from, m2_from, s2))
               * len(_find_range_double(m3_step)))
    print("Max = ", maximum)

    for i in _find_range(m1_from, m1_from, s1):
        motor_1.move_to_position(i)

        angles[0] = i

        for j in _find_range(m2_from, m2_from, s2):
            motor_2.move_to_position(j)

            angles[1] = j

            for k in _find_range_double(m3_step):
                c1 = time.time()
                motor_3.move_to_position(k)

                angles[2] = k

                m1 = angles[0]
                m2 = angles[1]
                m3 = angles[2]
                print("set angles")

                with nidaqmx.Task() as task:
                    task.ai_channels.add_ai_voltage_chan("myDAQ1/ai0:1")
                    task.timing.cfg_samp_clk_timing(
                        100000, source="", active_edge=Edge.RISING, sample_mode=AcquisitionType.FINITE,
                        samps_per_chan=10)

                    n = 0
                    measurement_points = input_data[9]
                    print("num = ", int(measurement_points))
                    print(type(measurement_points))

                    column_names = ["a", "b", "c", "d", "e"]
                    df = pd.DataFrame(columns=column_names)

                    while n < int(measurement_points):
                        aaa = task.read()
                        data = {
                            "a": [m1],
                            "b": [m2],
                            "c": [m3],
                            "d": [aaa[0]],
                            "e": [aaa[1]],
                        }
                        dp = pd.DataFrame(data)
                        df = pd.concat((df, dp), axis=0)
                        n += 1

                df2 = df.mean()
                print("m1:", df2.iloc[0], " m2:", df2.iloc[1], " m3:", df2.iloc[2])
                print(
                    "prumer Signal1:",
                    df2.iloc[3],
                    " a prumer Signal2:",
                    df2.iloc[4],
                )
                pomer = df2.iloc[3] / df2.iloc[4]
                print("Pomer je:", pomer)

                with open(name, "a") as f:
                    line = "{};{};{};{};{};{}".format(df2.iloc[0], df2.iloc[1], df2.iloc[2], df2.iloc[3], df2.iloc[4],
                                                      pomer)
                    print(line, file=f)

                progress_count += 1
                print("Progres count: ", progress_count)
                actual_progress = (100 / maximum) * progress_count
                print("Progress: ", actual_progress, " %")
                on_progress.emit(actual_progress)  # vyslani signalu

                c2 = time.time()
                dt = c2 - c1
                dn = maximum - progress_count
                dm = dt * dn
                dm = (dm / 20) + dm  # +20% na prejezdy M1 a M2
                print("dn = ", dn)
                print("dm = ", dm)
                on_progress2.emit(dm)  # vyslani signalu
                delta = timedelta(seconds=dm)
                (
                    days,
                    hours,
                    minutes,
                    seconds,
                ) = _days_hours_minutes_seconds(delta)
                print(
                    "Time to finish: ",
                    days,
                    "d",
                    hours,
                    "h",
                    minutes,
                    "m",
                    seconds,
                    "s",
                )


def scan_3d(motors, input_data, on_progress, on_progress2):
    motor_1 = motors[1]
    motor_2 = motors[2]
    motor_3 = motors[3]
    progress_count = 0

    print("3D measurement in progress...")

    # _____________________________________Cycle 3D START !!!!!___________________________________
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

    full_range = (len(motor_1_range) * len(motor_2_range) * len(motor_3_range))

    number_of_measurement_points = input_data[9]

    for i in motor_1_range:
        motor_1.move_to_position(i)

        angles[0] = i

        for j in motor_2_range:
            motor_2.move_to_position(j)

            angles[1] = j

            for k in motor_3_range:
                c1 = time.time()
                motor_3.move_to_position(k)

                angles[2] = k

                motor_1_position = angles[0]
                motor_2_position = angles[1]
                motor_3_position = angles[2]

                with nidaqmx.Task() as task:
                    task.ai_channels.add_ai_voltage_chan("myDAQ1/ai0:1")
                    task.timing.cfg_samp_clk_timing(
                        100000,
                        source="",
                        active_edge=Edge.RISING,
                        sample_mode=AcquisitionType.FINITE,
                        samps_per_chan=10)

                n = 0

                column_names = ["a", "b", "c", "d", "e"]
                measurement_data = pd.DataFrame(columns=column_names)

                while n < int(number_of_measurement_points):
                    sensor_data = [420, 69]  # task.read()
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

                df2 = measurement_data.mean()
                print("m1:", df2.iloc[0], " m2:", df2.iloc[1], " m3:", df2.iloc[2])
                print(
                    "prumer Signal1:",
                    df2.iloc[3],
                    " a prumer Signal2:",
                    df2.iloc[4],
                )
                pomer = df2.iloc[3] / df2.iloc[4]
                print("Pomer je:", pomer)

                with open(name, "a") as f:
                    line = "{};{};{};{};{};{}".format(df2.iloc[0], df2.iloc[1], df2.iloc[2], df2.iloc[3], df2.iloc[4], pomer)
                    print(line, file=f)

                progress_count += 1
                print("Progres count: ", progress_count)
                actual_progress = (100 / full_range) * progress_count
                print("Progress: ", actual_progress, " %")
                on_progress.emit(actual_progress)  # vyslani signalu

                c2 = time.time()
                dt = c2 - c1
                dn = full_range - progress_count
                dm = dt * dn
                dm = (dm / 20) + dm  # +20% na prejezdy M1 a M2
                print("dn = ", dn)
                print("dm = ", dm)
                on_progress2.emit(dm)  # vyslani signalu
                delta = timedelta(seconds=dm)
                (
                    days,
                    hours,
                    minutes,
                    seconds,
                ) = _days_hours_minutes_seconds(delta)
                print(
                    "Time to finish: ",
                    days,
                    "d",
                    hours,
                    "h",
                    minutes,
                    "m",
                    seconds,
                    "s",
                )
    print("Done")
