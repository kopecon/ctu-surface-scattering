import pandas as pd
from datetime import timedelta
import nidaqmx
from nidaqmx.constants import Edge
from nidaqmx.constants import AcquisitionType
import numpy as np
import time
from datetime import datetime


# TODO: Specify exceptions

def _find_range(start, stop, step):
    dx = int((stop - start) / step)
    return np.linspace(start, stop, endpoint=True, num=dx + 1)


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


def _update_progress(previous_progress, num):
    _progress_count = previous_progress + num


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
    _motor_1 = motors[1]
    _motor_2 = motors[2]
    _motor_3 = motors[3]
    _progress_count = 0
    print("1D measurement in progress...")
    # _____________________________________Cycle___________________________________
    angles = [0, 0, 0]

    name = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv"
    print("Writing", name)

    f1 = input_data[0]
    f1 = float(f1)
    s1 = 1

    f2 = input_data[3]
    f2 = float(f2)
    s2 = 1

    s3 = input_data[8]
    s3 = float(s3)

    maximum = (len(_find_range(f1, f1, s1))
               * len(_find_range(f2, f2, s2))
               * len(_find_range_double(s3)))
    print("Max = ", maximum)

    for i in _find_range(f1, f1, s1):
        _motor_1.move_to_position(i)

        angles.pop(0)
        angles.insert(0, i)

        time.sleep(2)

        for j in _find_range(f2, f2, s2):
            _motor_2.move_to_position(j)

            angles.pop(1)
            angles.insert(1, j)

            time.sleep(2)

            for k in _find_range_double(s3):
                c1 = time.time()
                _motor_3.move_to_position(k)

                angles.pop(2)
                angles.insert(2, k)

                m1 = angles[0]
                m2 = angles[1]
                m3 = angles[2]
                print("set angles")

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
                        num = input_data[9]
                        print("num = ", int(num))
                        print(type(num))

                        column_names = ["a", "b", "c", "d", "e"]
                        df = pd.DataFrame(columns=column_names)

                        while n < int(num):
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
                except:  # TODO Specify exception
                    pass

                df2 = df.mean()
                print("m1:", df2[0], " m2:", df2[1], " m3:", df2[2])
                print(
                    "prumer Signal1:",
                    df2[3],
                    " a prumer Signal2:",
                    df2[4],
                )
                pomer = df2[3] / df2[4]
                print("Pomer je:", pomer)

                with open(name, "a") as f:
                    line = "{};{};{};{};{};{}".format(df2[0], df2[1], df2[2], df2[3], df2[4], pomer)
                    print(line, file=f)

                _update_progress(_progress_count, 1)
                print("Progres count: ", _progress_count)
                actual_progress = (100 / maximum) * _progress_count
                print("Progress: ", actual_progress, " %")
                on_progress.emit(actual_progress)  # vyslani signalu

                c2 = time.time()
                dt = c2 - c1
                dn = maximum - _progress_count
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
    _motor_1 = motors[1]
    _motor_2 = motors[2]
    _motor_3 = motors[3]
    _progress_count = 0

    print("3D measurement in progress...")

    # _____________________________________Cycle 3D START !!!!!___________________________________
    angles = [0, 0, 0]

    name = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv"
    print("Writing", name)

    f1 = input_data[0]
    f1 = float(f1)
    t1 = input_data[1]
    t1 = float(t1)
    s1 = input_data[2]
    s1 = float(s1)

    f2 = input_data[3]
    f2 = float(f2)
    t2 = input_data[4]
    t2 = float(t2)
    s2 = input_data[5]
    s2 = float(s2)

    f3 = input_data[6]
    f3 = float(f3)
    t3 = input_data[7]
    t3 = float(t3)
    s3 = input_data[8]
    s3 = float(s3)

    maximum = (len(_find_range(f1, t1, s1))
               * len(_find_range(f2, t2, s2))
               * len(_find_range(f3, t3, s3)))
    print("Max = ", maximum)

    for i in _find_range(f1, t1, s1):
        print(_motor_1)
        _motor_1.move_to_position(i)

        angles.pop(0)
        angles.insert(0, i)

        time.sleep(2)

        for j in _find_range(f2, t2, s2):
            print("self.motor 2: ", f2, " ", t2, " ", s2)
            _motor_2.move_to_position(j)

            angles.pop(1)
            angles.insert(1, j)

            time.sleep(2)

            for k in _find_range(f3, t3, s3):
                c1 = time.time()
                _motor_3.move_to_position(k)

                angles.pop(2)
                angles.insert(2, k)

                m1 = angles[0]
                m2 = angles[1]
                m3 = angles[2]
                print("set angles")

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
                        num = input_data[9]

                        column_names = ["a", "b", "c", "d", "e"]
                        df = pd.DataFrame(columns=column_names)

                        while n < int(num):
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

                except:  # TODO Specify exception
                    pass
                df2 = df.mean()
                print("m1:", df2[0], " m2:", df2[1], " m3:", df2[2])
                print(
                    "prumer Signal1:",
                    df2[3],
                    " a prumer Signal2:",
                    df2[4],
                )
                pomer = df2[3] / df2[4]
                print("Pomer je:", pomer)

                with open(name, "a") as f:
                    line = "{};{};{};{};{};{}".format(df2[0], df2[1], df2[2], df2[3], df2[4], pomer)
                    print(line, file=f)

                _update_progress(_progress_count, 1)
                print("Progres count: ", _progress_count)
                actual_progress = (100 / maximum) * _progress_count
                print("Progress: ", actual_progress, " %")
                on_progress.emit(
                    actual_progress
                )  # vyslani signalu

                c2 = time.time()
                dt = c2 - c1
                dn = maximum - _progress_count
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
