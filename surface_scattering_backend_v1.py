# V8 + logy pro kontrolu u 3D mereni radek 536-555
# surface_scattering_v1 = GUI_GridnatacedlaV9 + Edit from "Kopecky Ondrej 2025"

from PySide6.QtCore import QThread, Signal

import os
import time
import numpy as np

import nidaqmx
from nidaqmx.constants import Edge
from nidaqmx.constants import AcquisitionType

from datetime import datetime

from pprint import pprint

from msl.equipment import (
    EquipmentRecord,
    ConnectionRecord,
    Backend,
)
from msl.equipment.resources.thorlabs import MotionControl

import pandas as pd
from datetime import timedelta


# Class representing the motor hardware
class Motor:
    def __init__(self, parent, motorID, polling_rate=200):
        self.motorID = motorID
        self._parent = parent
        self._position_device_unit = None
        self._position_real_unit = None
        self._polling_rate = 200
        self._controller = parent.connectedController

    def _wait(self, value: int):
        self._controller.clear_message_queue(self.motorID)
        message_type, message_id, _ = self._controller.wait_for_message(self.motorID)
        while message_type != 2 or message_id != value:
            position = self.getPosition()
            print(f"At position {position[0]} [device units] {position[1]} [real-world units]")
            message_type, message_id, _ = self._controller.wait_for_message(self.motorID)

    # Wrappers for controlling the motors
    def _load_settings(self):
        if self._parent is not None:
            self._controller.load_settings(self.motorID)
            print("Motor setting loaded.")
            time.sleep(2)  # TODO Check if delay is necessary and how long
        else:
            print("Not connected to controller.")

    def _start_polling(self, rate=200):
        if self._parent is not None:
            self._controller.start_polling(self.motorID, rate)
            print("Polling started...")
        else:
            print("Not connected to controller.")

    def _stop_polling(self):
        if self._parent is not None:
            self._controller.stop_polling(self.motorID)
            print("Polling stopped.")
        else:
            print("Not connected to controller.")

    def getPosition(self):
        self._position_device_unit = self._controller.get_position(self.motorID)
        self._position_real_unit = self._controller.get_real_value_from_device_unit(
            self.motorID, self._position_device_unit, "DISTANCE")
        print(f"At position: {self._position_device_unit} [device units]")
        print(f"At position: {self._position_real_unit} [real units]")
        return self._position_device_unit, self._position_real_unit

    def home(self):
        if self._parent is not None:
            self._load_settings()
            self._start_polling(rate=self._polling_rate)

            print("Initial position:")
            self.getPosition()
            print("Homing parameters:")
            print(self._controller.is_calibration_active(self.motorID))

            self._controller.home(self.motorID)
            print(f"Homing motor {self.motorID}...")
            self._wait(0)
            time.sleep(1)
            self.getPosition()
            self._stop_polling()
            print(f"Finishing homing motor {self.motorID}...")
            self._controller.disconnect()
            print("Controller disconnected.")
        else:
            print("Not connected to controller.")


# Class representing the motor controller hardware
class MotorController:
    def __init__(self, manufacturer: str, model: str, serial: str, address: str, backend: Backend):
        # ensure that the Kinesis folder is available on PATH
        os.environ["PATH"] += os.pathsep + "C:/Program Files/Thorlabs/Kinesis"

        # Model parameters
        self._manufacturer = manufacturer
        self._model = model
        self._serial = serial
        self._address = address
        self._backend = backend
        self._record = EquipmentRecord(
            manufacturer=self._manufacturer, model=self._model,  # update for your device
            serial=self._serial,  # update for your device
            connection=ConnectionRecord(address=self._address, backend=self._backend))
        self.connectedController = None
        self.channels = []  # List of available channels
        self.motors = [0]  # List of available motors (motors are indexed from 1, so let 0 index be 0)

        # But we know there are 3 motors, so we add a variable for each motor
        self.motor_1 = None
        self.motor_2 = None
        self.motor_3 = None

    def connect(self):
        try:
            MotionControl.build_device_list()
            print("Device list built successfully.")

            self.connectedController = self._record.connect()
            print("Record set up successfully.")

            self.channels = list(
                range(0, self.connectedController.max_channel_count()))  # Scan how many channels are on the device
            print("Identifying motors...")
            self.motors = [0]  # Erase previously loaded motors
            # Create list of available motors
            for i, chanel in enumerate(self.channels):
                self.motors.append(Motor(self, i+1))  # i starts indexing from 0 but motor ID starts from 1 => i+1
                print(f"    Motor {i+1} identified.")

            # TODO fix motor assignment when no channels found
            """
            # Assign variable for each motor separately
            self.motor_1 = self.motors[0]
            self.motor_2 = self.motors[1]
            self.motor_3 = self.motors[2]
            """
            print("Connection done.")

        except OSError:
            print("No devices found.")


class WorkerMove(QThread):
    on_progress = Signal(int)
    on_progress2 = Signal(float)

    def __init__(self, inputData):
        super().__init__()
        self.inputData = inputData
        self.progressCount = 0

    def wait(self, value, channel):
        self.motor.clear_message_queue(channel)
        message_type, message_id, _ = self.motor.wait_for_message(channel)
        while message_type != 2 or message_id != value:
            position = self.motor.get_position(channel)
            real = self.motor.get_real_value_from_device_unit(
                channel, position, "DISTANCE"
            )
            print(
                "  at position {} [device units] {:.3f} [real-world units]".format(
                    position, real
                )
            )
            message_type, message_id, _ = self.motor.wait_for_message(channel)

    def frange(self, start, stop, step):
        dx = int((stop - start) / step)
        return np.linspace(start, stop, endpoint=True, num=dx + 1)

    def frangedouble(self, step):
        self.START1 = 270
        self.STOP1 = 360
        self.START2 = 0
        self.STOP2 = 90
        dx1 = int((self.STOP1 - self.START1) / step)
        dx2 = int((self.STOP2 - self.START2) / step)
        point1 = np.linspace(
            self.START1, self.STOP1, endpoint=True, num=dx1 + 1
        )
        point2 = np.linspace(
            self.START2, self.STOP2, endpoint=True, num=dx2 + 1
        )
        point0 = np.concatenate((point1, point2))
        point = np.delete(point0, np.where(point0 == 360))
        return point

    def udateProgress(self, num):
        self.progressCount = self.progressCount + num

    def days_hours_minutes_seconds(self, dt):
        return (
            dt.days,  # days
            dt.seconds // 3600,  # hours
            (dt.seconds // 60) % 60,  # minutes
            dt.seconds
            - ((dt.seconds // 3600) * 3600)
            - ((dt.seconds % 3600 // 60) * 60),
            # seconds
        )

    def run(self):
        # print imputdata from GUI
        print("Data(WorkerMove.run): ", self.inputData)

        # ensure that the Kinesis folder is available on PATH
        os.environ["PATH"] += os.pathsep + "C:/Program Files/Thorlabs/Kinesis"
        print("building PATH to Kinesis ...")

        record = EquipmentRecord(
            manufacturer="Thorlabs",
            model="BSC203",  # update for your device
            serial="70224414",  # update for your device
            connection=ConnectionRecord(
                address="SDK::Thorlabs.MotionControl.Benchtop.StepperMotor.dll",
                backend=Backend.MSL,
            ),
        )
        print("record setup ...")

        # avoid the FT_DeviceNotFound error
        MotionControl.build_device_list()
        print("building list ...")

        # connect to the Benchtop Stepper Motor
        self.motor = record.connect()
        print("Connected to {}".format(self.motor))

        # all available channels from the device
        print(
            "Available channels are: {}".format(self.motor.max_channel_count())
        )

        # set the channel number of the Benchtop Stepper Motor to communicate with
        channel = [1, 2, 3]

        if self.inputData[10] == 1:
            print("1D measurement in progress...")
            # _____________________________________Cycle___________________________________
            angles = [0, 0, 0]

            name = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv"
            print("Writing", name)

            f1 = self.inputData[0]
            f1 = float(f1)
            s1 = 1

            f2 = self.inputData[3]
            f2 = float(f2)
            s2 = 1

            s3 = self.inputData[8]
            s3 = float(s3)

            self.max = (
                    len(self.frange(f1, f1, s1))
                    * len(self.frange(f2, f2, s2))
                    * len(self.frangedouble(s3))
            )
            print("Max = ", self.max)

            for i in self.frange(f1, f1, s1):
                self.motor.load_settings(channel[0])
                time.sleep(1)
                self.motor.start_polling(channel[0], 200)
                self.motor.move_to_position(channel[0],
                                            self.motor.get_device_unit_from_real_value(channel[0], i, "DISTANCE"), )
                self.wait(1, channel[0])
                self.motor.stop_polling(channel[0])

                angles.pop(0)
                angles.insert(0, i)

                time.sleep(2)

                for i in self.frange(f2, f2, s2):
                    self.motor.load_settings(channel[1])
                    time.sleep(1)
                    self.motor.start_polling(channel[1], 200)
                    self.motor.move_to_position(
                        channel[1],
                        self.motor.get_device_unit_from_real_value(
                            channel[1], i, "DISTANCE"
                        ),
                    )
                    self.wait(1, channel[1])
                    self.motor.stop_polling(channel[1])

                    angles.pop(1)
                    angles.insert(1, i)

                    time.sleep(2)

                    for i in self.frangedouble(s3):
                        c1 = time.time()
                        self.motor.load_settings(channel[2])
                        time.sleep(1)
                        self.motor.start_polling(channel[2], 200)
                        self.motor.move_to_position(
                            channel[2],
                            self.motor.get_device_unit_from_real_value(
                                channel[2], i, "DISTANCE"
                            ),
                        )
                        self.wait(1, channel[2])
                        self.motor.stop_polling(channel[2])

                        angles.pop(2)
                        angles.insert(2, i)

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

                                i = 0
                                num = self.inputData[9]
                                print("num = ", int(num))
                                print(type(num))

                                column_names = ["a", "b", "c", "d", "e"]
                                df = pd.DataFrame(columns=column_names)

                                while i < int(num):
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
                                    i += 1

                        except:
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
                            line = "{};{};{};{};{};{}".format(
                                df2[0], df2[1], df2[2], df2[3], df2[4], pomer
                            )
                            print(line, file=f)

                        self.udateProgress(1)
                        print("Progres count: ", self.progressCount)
                        self.actual_progress = (
                                                       100 / self.max
                                               ) * self.progressCount
                        print("Progress: ", self.actual_progress, " %")
                        self.on_progress.emit(
                            self.actual_progress
                        )  # vyslani signalu

                        c2 = time.time()
                        dt = c2 - c1
                        dn = self.max - self.progressCount
                        dm = dt * dn
                        dm = (dm / 20) + dm  # +20% na prejezdy M1 a M2
                        print("dn = ", dn)
                        print("dm = ", dm)
                        self.on_progress2.emit(dm)  # vyslani signalu
                        delta = timedelta(seconds=dm)
                        (
                            days,
                            hours,
                            minutes,
                            seconds,
                        ) = self.days_hours_minutes_seconds(delta)
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

        else:
            print("3D measurment in progress...")

            # _____________________________________Cycle 3D START !!!!!___________________________________
            angles = [0, 0, 0]

            name = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv"
            print("Writing", name)

            f1 = self.inputData[0]
            f1 = float(f1)
            t1 = self.inputData[1]
            t1 = float(t1)
            s1 = self.inputData[2]
            s1 = float(s1)

            f2 = self.inputData[3]
            f2 = float(f2)
            t2 = self.inputData[4]
            t2 = float(t2)
            s2 = self.inputData[5]
            s2 = float(s2)

            f3 = self.inputData[6]
            f3 = float(f3)
            t3 = self.inputData[7]
            t3 = float(t3)
            s3 = self.inputData[8]
            s3 = float(s3)

            self.max = (
                    len(self.frange(f1, t1, s1))
                    * len(self.frange(f2, t2, s2))
                    * len(self.frange(f3, t3, s3))
            )
            print("Max = ", max)

            for i in self.frange(f1, t1, s1):
                self.motor.load_settings(channel[0])
                time.sleep(1)
                self.motor.start_polling(channel[0], 200)
                self.motor.move_to_position(
                    channel[0],
                    self.motor.get_device_unit_from_real_value(
                        channel[0], i, "DISTANCE"
                    ),
                )
                self.wait(1, channel[0])
                self.motor.stop_polling(channel[0])

                angles.pop(0)
                angles.insert(0, i)

                time.sleep(2)

                for i in self.frange(f2, t2, s2):
                    print("Motor 2: ", f2, " ", t2, " ", s2)
                    self.motor.load_settings(channel[1])
                    time.sleep(1)
                    self.motor.start_polling(channel[1], 200)
                    self.motor.move_to_position(
                        channel[1],
                        self.motor.get_device_unit_from_real_value(
                            channel[1], i, "DISTANCE"
                        ),
                    )
                    self.wait(1, channel[1])
                    self.motor.stop_polling(channel[1])

                    angles.pop(1)
                    angles.insert(1, i)

                    time.sleep(2)

                    for i in self.frange(f3, t3, s3):
                        c1 = time.time()
                        self.motor.load_settings(channel[2])
                        time.sleep(1)
                        self.motor.start_polling(channel[2], 200)
                        self.motor.move_to_position(
                            channel[2],
                            self.motor.get_device_unit_from_real_value(
                                channel[2], i, "DISTANCE"
                            ),
                        )
                        self.wait(1, channel[2])
                        self.motor.stop_polling(channel[2])

                        angles.pop(2)
                        angles.insert(2, i)

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

                                i = 0
                                num = self.inputData[9]

                                column_names = ["a", "b", "c", "d", "e"]
                                df = pd.DataFrame(columns=column_names)

                                while i < int(num):
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
                                    i += 1

                        except:
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
                            line = "{};{};{};{};{};{}".format(
                                df2[0], df2[1], df2[2], df2[3], df2[4], pomer
                            )
                            print(line, file=f)

                        self.udateProgress(1)
                        print("Progres count: ", self.progressCount)
                        self.actual_progress = (
                                                       100 / self.max
                                               ) * self.progressCount
                        print("Progress: ", self.actual_progress, " %")
                        self.on_progress.emit(
                            self.actual_progress
                        )  # vyslani signalu

                        c2 = time.time()
                        dt = c2 - c1
                        dn = self.max - self.progressCount
                        dm = dt * dn
                        dm = (dm / 20) + dm  # +20% na prejezdy M1 a M2
                        print("dn = ", dn)
                        print("dm = ", dm)
                        self.on_progress2.emit(dm)  # vyslani signalu
                        delta = timedelta(seconds=dm)
                        (
                            days,
                            hours,
                            minutes,
                            seconds,
                        ) = self.days_hours_minutes_seconds(delta)
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

        # ------------------------------------Disconnect the device--------------------

        self.motor.disconnect()

        # you can access the default settings
        # for the motor to pass to the set_*() methods

        print("\nThe default motor settings are:")
        pprint(self.motor.settings)


# Define motor controller based on the hardware in the lab:
BSC203ThreeChannelBenchtopStepperMotorController = MotorController(
    manufacturer="Thorlabs",
    model="BSC203",
    serial="70224414",
    address="SDK::Thorlabs.MotionControl.Benchtop.StepperMotor.dll",
    backend=Backend.MSL)
