# V8 + logy pro kontrolu u 3D mereni radek 536-555
# surface_scattering_v1 = GUI_GridnatacedlaV9 + Edit from "Kopecky Ondrej 2025"


from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QLabel,
    QWidget,
    QGridLayout,
    QLineEdit,
    QCheckBox,
)
from PySide6.QtCore import QThread, Signal, QSize, Qt
import sys

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
from PySide6.QtGui import QPixmap

print("library import done.")


class WorkerHome(QThread):
    on_progress = Signal(int)

    def __init__(self, motornum):
        super().__init__()
        self.motornum = motornum

    def wait(self, value: int, channel: int):
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

    def run(self):
        # print("for motor:", motornum)  # cislo motoru z click button
        print("my Motor: ", self.motornum)

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
        # channel = 1
        channel = self.motornum

        # __________________________________ Homing the channel 1 __________________________________

        # load the configuration settings, so that we can call
        # the get_real_value_from_device_unit() method for the channel 1
        self.motor.load_settings(channel)
        time.sleep(1)
        print("Loaded setting for motor ", channel)

        # the SBC_Open(serialNo) function in Kinesis is non-blocking and therefore we
        # should add a delay for Kinesis to establish communication with the serial port
        time.sleep(1)

        # start polling at 200 ms
        self.motor.start_polling(channel, 200)

        # home the channel 1
        print("Homing...")
        self.motor.home(channel)
        self.wait(0, channel)
        time.sleep(1)
        print(
            "Homing done. At position {} [device units]".format(
                self.motor.get_position(channel)
            )
        )

        # get absolute position for the channel 1
        print("Absolute position is: ")
        position = self.motor.get_position(channel)
        real = self.motor.get_real_value_from_device_unit(
            channel, position, "DISTANCE"
        )
        print(" >>>>>{} [real-world units]".format(real))

        # stop polling the channel1
        self.motor.stop_polling(channel)

        time.sleep(2)

        # ------------------------------------Disconnect the device-------------------------------------

        self.motor.disconnect()

        print("Homing done.")


class WorkerMove(QThread):
    on_progress = Signal(int)
    on_progress2 = Signal(float)

    def __init__(self, imputdata):
        super().__init__()
        self.imputdata = imputdata
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
        print("Data(WorkerMove.run): ", self.imputdata)

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

        if self.imputdata[10] == 1:
            print("1D measurement in progress...")
            # _____________________________________Cycle___________________________________
            angles = [0, 0, 0]

            name = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + ".csv"
            print("Writing", name)

            f1 = self.imputdata[0]
            f1 = float(f1)
            s1 = 1

            f2 = self.imputdata[3]
            f2 = float(f2)
            s2 = 1

            s3 = self.imputdata[8]
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
                                            self.motor.get_device_unit_from_real_value(channel[0], i, "DISTANCE"),)
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
                                num = self.imputdata[9]
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

            f1 = self.imputdata[0]
            f1 = float(f1)
            t1 = self.imputdata[1]
            t1 = float(t1)
            s1 = self.imputdata[2]
            s1 = float(s1)

            f2 = self.imputdata[3]
            f2 = float(f2)
            t2 = self.imputdata[4]
            t2 = float(t2)
            s2 = self.imputdata[5]
            s2 = float(s2)

            f3 = self.imputdata[6]
            f3 = float(f3)
            t3 = self.imputdata[7]
            t3 = float(t3)
            s3 = self.imputdata[8]
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
                                num = self.imputdata[9]

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


class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Thorlab 3 Wheel")
        self.setFixedSize(QSize(600, 600))

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        self.createLabels()
        self.createLineEdits()
        self.createButtons()
        self.createProgressBars()
        self.createLogo()
        self.createCheckboxs()

        self.layout = QGridLayout()
        centralWidget.setLayout(self.layout)
        self.layout.addWidget(self.labelMSETUPtitle, 0, 0, 1, 1)
        self.layout.addWidget(self.labelM1from, 1, 1, 1, 1)
        self.layout.addWidget(self.labelM1to, 1, 2, 1, 1)
        self.layout.addWidget(self.labelM1step, 1, 3, 1, 1)
        self.layout.addWidget(self.labelM1, 2, 0, 1, 1)
        self.layout.addWidget(self.labelM2from, 4, 1, 1, 1)
        self.layout.addWidget(self.labelM2to, 4, 2, 1, 1)
        self.layout.addWidget(self.labelM2step, 4, 3, 1, 1)
        self.layout.addWidget(self.labelM2, 5, 0, 1, 1)
        self.layout.addWidget(self.labelM3from, 6, 1, 1, 1)
        self.layout.addWidget(self.labelM3to, 6, 2, 1, 1)
        self.layout.addWidget(self.labelM3step, 6, 3, 1, 1)
        self.layout.addWidget(self.labelM3, 7, 0, 1, 1)
        self.layout.addWidget(self.labelMESSETUPtitle, 9, 0, 1, 1)
        self.layout.addWidget(self.labelMESnum, 10, 0, 1, 1)
        self.layout.addWidget(self.labelMESn, 10, 2, 1, 1)
        self.layout.addWidget(self.labelHOMEtitle, 12, 0, 1, 1)
        self.layout.addWidget(self.labelTIMEFtitle, 12, 3, 1, 1)
        self.layout.addWidget(self.labelTIMEFvalue, 12, 4, 1, 1)
        self.layout.addWidget(self.M1FROMvalue, 2, 1, 1, 1)
        self.layout.addWidget(self.M1TOvalue, 2, 2, 1, 1)
        self.layout.addWidget(self.M1STEPvalue, 2, 3, 1, 1)
        self.layout.addWidget(self.M2FROMvalue, 5, 1, 1, 1)
        self.layout.addWidget(self.M2TOvalue, 5, 2, 1, 1)
        self.layout.addWidget(self.M2STEPvalue, 5, 3, 1, 1)
        self.layout.addWidget(self.M3FROMvalue, 7, 1, 1, 1)
        self.layout.addWidget(self.M3TOvalue, 7, 2, 1, 1)
        self.layout.addWidget(self.M3STEPvalue, 7, 3, 1, 1)
        self.layout.addWidget(self.MESPOINTSvalue, 10, 1, 1, 1)
        self.layout.addWidget(self.STARTMESS, 11, 3, 1, 1)
        self.layout.addWidget(self.HOME1, 13, 1, 1, 1)
        self.layout.addWidget(self.HOME2, 14, 1, 1, 1)
        self.layout.addWidget(self.HOME3, 15, 1, 1, 1)
        self.layout.addWidget(self.Progress, 13, 3, 1, 2)
        self.layout.addWidget(self.urlLabel, 17, 4, 1, 1)
        self.layout.addWidget(self.mylogo, 0, 4, 1, 2)
        self.layout.addWidget(self.onedmeasurement, 11, 4, 1, 1)

    def createLabels(self):
        self.labelMSETUPtitle = self.createLabel("Motors Setup:")

        self.labelM1from = self.createLabel("From")
        self.labelM1to = self.createLabel("To")
        self.labelM1step = self.createLabel("Step")
        self.labelM1 = self.createLabel("Motor 1")

        self.labelM2from = self.createLabel("From")
        self.labelM2to = self.createLabel("To")
        self.labelM2step = self.createLabel("Step")
        self.labelM2 = self.createLabel("Motor 2")

        self.labelM3from = self.createLabel("From")
        self.labelM3to = self.createLabel("To")
        self.labelM3step = self.createLabel("Step")
        self.labelM3 = self.createLabel("Motor 3")

        self.labelMESSETUPtitle = self.createLabel("Measurement Setup:")

        self.labelMESnum = self.createLabel("N Measurement points")
        self.labelMESn = self.createLabel("[n]")

        self.labelHOMEtitle = self.createLabel("Homing:")

        self.labelTIMEFtitle = self.createLabel("Time to Finish:")
        self.labelTIMEFvalue = self.createLabel("0d 0h 0m 0s")

        self.urlLabel = self.createLabel(
            f"<a href='https://www.numsolution.cz/'>https://www.numsolution.cz/</a>"
        )
        self.urlLabel.setOpenExternalLinks(True)

    def createLabel(self, text: str) -> QLabel:
        label = QLabel()
        label.setText(text)
        return label

    def createLineEdits(self):
        self.M1FROMvalue = self.createLineEdit("0")
        self.M1TOvalue = self.createLineEdit("90")
        self.M1STEPvalue = self.createLineEdit("30")

        self.M2FROMvalue = self.createLineEdit("90")
        self.M2TOvalue = self.createLineEdit("180")
        self.M2STEPvalue = self.createLineEdit("30")

        self.M3FROMvalue = self.createLineEdit("0")
        self.M3TOvalue = self.createLineEdit("90")
        self.M3STEPvalue = self.createLineEdit("30")

        self.MESPOINTSvalue = self.createLineEdit("500")

    def createLineEdit(self, text: str) -> QLineEdit:
        lineEdit = QLineEdit()
        lineEdit.setText(text)
        return lineEdit

    def createButtons(self):
        self.STARTMESS = self.createButton("Start Measurement")
        self.HOME1 = self.createButton("Motor 1 Home")
        self.HOME2 = self.createButton("Motor 2 Home")
        self.HOME3 = self.createButton("Motor 3 Home")

        self.STARTMESS.clicked.connect(lambda: self.functionMove())

        self.HOME1.clicked.connect(
            lambda: self.functionHome(1, self.M1FROMvalue.text())
        )
        self.HOME2.clicked.connect(
            lambda: self.functionHome(2, self.M2FROMvalue.text())
        )
        self.HOME3.clicked.connect(
            lambda: self.functionHome(3, self.M3FROMvalue.text())
        )

    def createButton(self, text: str) -> QPushButton:
        pushButton = QPushButton()
        pushButton.setText(text)
        return pushButton

    def createProgressBars(self):
        self.Progress = self.createProgressBar(0)

    def createProgressBar(self, num: int) -> QProgressBar:
        progressBar = QProgressBar()
        progressBar.setValue(num)
        return progressBar

    def createLogo(self):
        self.LOGO = QPixmap("NUMlogo_200x93.png")
        self.LOGO = self.LOGO.scaledToWidth(100, Qt.SmoothTransformation)
        self.mylogo = QLabel()
        self.mylogo.setAlignment(Qt.AlignRight)
        self.mylogo.setPixmap(self.LOGO)

    def createCheckboxs(self):
        self.onedmeasurement = QCheckBox("1D Measurement", self)
        self.onedmeasurement.setChecked(False)
        self.onedmeasurement.clicked.connect(self.functionOneDmeasurement)

    def functionOneDmeasurement(self):
        if self.onedmeasurement.isChecked() == True:
            self.M1TOvalue.setEnabled(False)
            self.M1STEPvalue.setEnabled(False)
            self.M2TOvalue.setEnabled(False)
            self.M2STEPvalue.setEnabled(False)
            self.M3FROMvalue.setEnabled(False)
            self.M3TOvalue.setEnabled(False)

        else:
            self.M1TOvalue.setEnabled(True)
            self.M1STEPvalue.setEnabled(True)
            self.M2TOvalue.setEnabled(True)
            self.M2STEPvalue.setEnabled(True)
            self.M3FROMvalue.setEnabled(True)
            self.M3TOvalue.setEnabled(True)

    def functionMove(self):
        if self.onedmeasurement.isChecked() == True:
            self.oned = 1
            print("1D measurement ON")
        else:
            self.oned = 0
            print("1D measurement OFF")

        self.imputdata = [
            self.M1FROMvalue.text(),
            self.M1TOvalue.text(),
            self.M1STEPvalue.text(),
            self.M2FROMvalue.text(),
            self.M2TOvalue.text(),
            self.M2STEPvalue.text(),
            self.M3FROMvalue.text(),
            self.M3TOvalue.text(),
            self.M3STEPvalue.text(),
            self.MESPOINTSvalue.text(),
            self.oned,
        ]
        print("Data(functionMove): ", self.imputdata)
        self.myworkermove = WorkerMove(self.imputdata)
        self.myworkermove.finished.connect(
            self.finihedMove
        )  # propojeni signalu
        self.myworkermove.on_progress.connect(
            self.progressMove
        )  # propojeni signalu

        self.myworkermove.on_progress2.connect(
            self.progressMove2
        )  # propojeni signalu

        print("Run Move Function")

        self.STARTMESS.setEnabled(False)
        self.HOME1.setEnabled(False)
        self.HOME2.setEnabled(False)
        self.HOME3.setEnabled(False)

        self.myworkermove.start()

    def finihedMove(self):
        self.Progress.setValue(100)
        self.STARTMESS.setEnabled(True)
        self.HOME1.setEnabled(True)
        self.HOME2.setEnabled(True)
        self.HOME3.setEnabled(True)
        print("konec")

    def progressMove(self, n):
        self.Progress.setValue(n)
        print("Progress num:", n)

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

    def progressMove2(self, dm: float):
        delta = timedelta(seconds=dm)
        (days, hours, minutes, seconds) = self.days_hours_minutes_seconds(
            delta
        )
        n = (
            str(days)
            + "d "
            + str(hours)
            + "h "
            + str(minutes)
            + "m "
            + str(seconds)
            + "s"
        )
        self.labelTIMEFvalue.setText(n)

    def functionHome(self, motornum, M1Fromvalue):
        self.myworkerhome = WorkerHome(motornum)
        self.myworkerhome.finished.connect(
            self.finihedHome
        )  # propojeni signalu
        self.myworkerhome.on_progress.connect(
            self.progressHome
        )  # propojeni signalu

        print("Clicket motor:", motornum)
        print("self.MXFROMvalue:", M1Fromvalue)
        self.STARTMESS.setEnabled(False)
        self.HOME1.setEnabled(False)
        self.HOME2.setEnabled(False)
        self.HOME3.setEnabled(False)

        self.myworkerhome.start()

    def finihedHome(self):
        self.Progress.setValue(0)
        self.STARTMESS.setEnabled(True)
        self.HOME1.setEnabled(True)
        self.HOME2.setEnabled(True)
        self.HOME3.setEnabled(True)
        print("konec")

    def progressHome(self, n):
        self.Progress.setValue(n)
        print("Progress num:", n)


# Create the Qt Applocation
app = QApplication([])
window = Window()
window.show()
sys.exit(app.exec())
