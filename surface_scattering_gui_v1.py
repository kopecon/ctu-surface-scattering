from PySide6.QtGui import QPixmap
from PySide6.QtCore import QSize, Qt, QThread, Signal
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

import sys
from datetime import timedelta

import surface_scattering_backend_v1
# Custom packages from this project
from surface_scattering_backend_v1 import WorkerHome, WorkerMove


print("Library import done.")


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        _centralWidget = QWidget()
        self.setCentralWidget(_centralWidget)
        self._layout = QGridLayout()
        _centralWidget.setLayout(self._layout)

        self.setWindowTitle("Thorlab 3 Wheel")
        self.setFixedSize(QSize(600, 600))

        # Measurement arguments:
        self.inputData = []
        self.oneD = 0

        # Labels
        _labelMotorSetupTitle = self.label("Motors Setup:")

        _labelM1from = self.label("From")
        _labelM1to = self.label("To")
        _labelM1step = self.label("Step")
        _labelM1 = self.label("Motor 1")

        _labelM2from = self.label("From")
        _labelM2to = self.label("To")
        _labelM2step = self.label("Step")
        _labelM2 = self.label("Motor 2")

        _labelM3from = self.label("From")
        _labelM3to = self.label("To")
        _labelM3step = self.label("Step")
        _labelM3 = self.label("Motor 3")

        _labelMeasurementSetupTitle = self.label("Measurement Setup:")

        _labelMeasurementNum = self.label("N Measurement points")
        _labelMeasurementN = self.label("[n]")

        _labelHomeTitle = self.label("Homing:")

        _labelTimeToFinishTitle = self.label("Time to Finish:")
        self._labelTimeToFinishValue = self.label("0d 0h 0m 0s")

        _urlLabel = self.label(
            f"<a href='https://www.numsolution.cz/'>https://www.numsolution.cz/</a>"
        )
        _urlLabel.setOpenExternalLinks(True)

        # Line edits
        self._M1FROMValue = self.lineEdit("0")
        self._M1TOValue = self.lineEdit("90")
        self._M1STEPValue = self.lineEdit("30")

        self._M2FROMValue = self.lineEdit("90")
        self._M2TOValue = self.lineEdit("180")
        self._M2STEPValue = self.lineEdit("30")

        self._M3FROMValue = self.lineEdit("0")
        self._M3TOValue = self.lineEdit("90")
        self._M3STEPValue = self.lineEdit("30")

        self._MESPOINTSValue = self.lineEdit("500")

        # Buttons
        self._startMeasurement = self.pushButton("Start Measurement")
        self._Home1 = self.pushButton("Motor 1 Home")
        self._Home2 = self.pushButton("Motor 2 Home")
        self._Home3 = self.pushButton("Motor 3 Home")
        self._Home1_new = self.pushButton("Motor 1 Home new")

        self._startMeasurement.clicked.connect(lambda: self.functionMove())

        self._Home1.clicked.connect(lambda: self.functionHome(1, self._M1FROMValue.text()))
        self._Home2.clicked.connect(lambda: self.functionHome(2, self._M2FROMValue.text()))
        self._Home3.clicked.connect(lambda: self.functionHome(3, self._M3FROMValue.text()))
        self._Home1_new.clicked.connect(lambda: self.startHomingSelectedMotor(1))

        # Progress bar
        self._progressBar = self.createProgressBar(0)

        # Checkbox
        self._oneDMeasurement = QCheckBox("1D Measurement", self)
        self._oneDMeasurement.setChecked(False)
        self._oneDMeasurement.clicked.connect(self.disableValueEditing)

        # Logo
        logo = self.createLogo()

        # Place and display created widgets
        self._layout.addWidget(_labelMotorSetupTitle, 0, 0, 1, 1)
        self._layout.addWidget(_labelM1from, 1, 1, 1, 1)
        self._layout.addWidget(_labelM1to, 1, 2, 1, 1)
        self._layout.addWidget(_labelM1step, 1, 3, 1, 1)
        self._layout.addWidget(_labelM1, 2, 0, 1, 1)
        self._layout.addWidget(_labelM2from, 4, 1, 1, 1)
        self._layout.addWidget(_labelM2to, 4, 2, 1, 1)
        self._layout.addWidget(_labelM2step, 4, 3, 1, 1)
        self._layout.addWidget(_labelM2, 5, 0, 1, 1)
        self._layout.addWidget(_labelM3from, 6, 1, 1, 1)
        self._layout.addWidget(_labelM3to, 6, 2, 1, 1)
        self._layout.addWidget(_labelM3step, 6, 3, 1, 1)
        self._layout.addWidget(_labelM3, 7, 0, 1, 1)
        self._layout.addWidget(_labelMeasurementSetupTitle, 9, 0, 1, 1)
        self._layout.addWidget(_labelMeasurementNum, 10, 0, 1, 1)
        self._layout.addWidget(_labelMeasurementN, 10, 2, 1, 1)
        self._layout.addWidget(_labelHomeTitle, 12, 0, 1, 1)
        self._layout.addWidget(_labelTimeToFinishTitle, 12, 3, 1, 1)
        self._layout.addWidget(self._labelTimeToFinishValue, 12, 4, 1, 1)
        self._layout.addWidget(self._M1FROMValue, 2, 1, 1, 1)
        self._layout.addWidget(self._M1TOValue, 2, 2, 1, 1)
        self._layout.addWidget(self._M1STEPValue, 2, 3, 1, 1)
        self._layout.addWidget(self._M2FROMValue, 5, 1, 1, 1)
        self._layout.addWidget(self._M2TOValue, 5, 2, 1, 1)
        self._layout.addWidget(self._M2STEPValue, 5, 3, 1, 1)
        self._layout.addWidget(self._M3FROMValue, 7, 1, 1, 1)
        self._layout.addWidget(self._M3TOValue, 7, 2, 1, 1)
        self._layout.addWidget(self._M3STEPValue, 7, 3, 1, 1)
        self._layout.addWidget(self._MESPOINTSValue, 10, 1, 1, 1)
        self._layout.addWidget(self._startMeasurement, 11, 3, 1, 1)
        self._layout.addWidget(self._Home1, 13, 1, 1, 1)
        self._layout.addWidget(self._Home2, 14, 1, 1, 1)
        self._layout.addWidget(self._Home3, 15, 1, 1, 1)
        self._layout.addWidget(self._Home1_new, 16, 1, 1, 1)
        self._layout.addWidget(self._progressBar, 13, 3, 1, 2)
        self._layout.addWidget(_urlLabel, 17, 4, 1, 1)
        self._layout.addWidget(logo, 0, 4, 1, 2)
        self._layout.addWidget(self._oneDMeasurement, 11, 4, 1, 1)

    # --------- Functions to make creating widgets easier ----------------
    @staticmethod
    def label(text: str) -> QLabel:
        label = QLabel()
        label.setText(text)
        return label

    @staticmethod
    def lineEdit(text: str) -> QLineEdit:
        lineEdit = QLineEdit()
        lineEdit.setText(text)
        return lineEdit

    @staticmethod
    def pushButton(text: str) -> QPushButton:
        pushButton = QPushButton()
        pushButton.setText(text)
        return pushButton

    @staticmethod
    def createProgressBar(num: int) -> QProgressBar:
        progressBar = QProgressBar()
        progressBar.setValue(num)
        return progressBar

    # -----------------------------------------------------------------------

    def createLogo(self):
        logo_png = QPixmap("NUMlogo_200x93.png")
        logo_png = logo_png.scaledToWidth(100, Qt.TransformationMode.SmoothTransformation)
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignRight)
        logo.setPixmap(logo_png)
        return logo

    def disableValueEditing(self):
        if self._oneDMeasurement.isChecked():
            self._M1TOValue.setEnabled(False)
            self._M1STEPValue.setEnabled(False)
            self._M2TOValue.setEnabled(False)
            self._M2STEPValue.setEnabled(False)
            self._M3FROMValue.setEnabled(False)
            self._M3TOValue.setEnabled(False)

        else:
            self._M1TOValue.setEnabled(True)
            self._M1STEPValue.setEnabled(True)
            self._M2TOValue.setEnabled(True)
            self._M2STEPValue.setEnabled(True)
            self._M3FROMValue.setEnabled(True)
            self._M3TOValue.setEnabled(True)

    def updateLayoutAfterFinishedMove(self):
        self._progressBar.setValue(0)
        self._startMeasurement.setEnabled(True)
        self._Home1.setEnabled(True)
        self._Home2.setEnabled(True)
        self._Home3.setEnabled(True)

    def daysHoursMinutesSeconds(self, dt):
        return (
            dt.days,  # days
            dt.seconds // 3600,  # hours
            (dt.seconds // 60) % 60,  # minutes
            dt.seconds
            - ((dt.seconds // 3600) * 3600)
            - ((dt.seconds % 3600 // 60) * 60),
            # seconds
        )

    def updateProgressBar(self, n):
        self._progressBar.setValue(n)
        print("Progress num:", n)

    def updateProgressBarLabel(self, dm: float):
        delta = timedelta(seconds=dm)
        (days, hours, minutes, seconds) = self.daysHoursMinutesSeconds(delta)
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
        self._labelTimeToFinishValue.setText(n)

    def startHomingSelectedMotor(self, motorID):
        self.myworkerhome = HomingThread(motorID)
        self.myworkerhome.finished.connect(self.updateLayoutAfterFinishedMove)  # propojeni signalu
        self.myworkerhome.on_progress.connect(self.updateProgressBar)  # propojeni signalu

        print("Clicked motor:", motorID)
        self._startMeasurement.setEnabled(False)
        self._Home1.setEnabled(False)
        self._Home2.setEnabled(False)
        self._Home3.setEnabled(False)

        self.myworkerhome.start()

    def functionHome(self, motorNum, MXFromValue):
        self.myworkerhome = WorkerHome(motorNum)
        self.myworkerhome.finished.connect(self.updateLayoutAfterFinishedMove)  # propojeni signalu
        self.myworkerhome.on_progress.connect(self.updateProgressBar)  # propojeni signalu

        print("Clicked motor:", motorNum)
        print("self.MXFromValue:", MXFromValue)
        self._startMeasurement.setEnabled(False)
        self._Home1.setEnabled(False)
        self._Home2.setEnabled(False)
        self._Home3.setEnabled(False)

        self.myworkerhome.start()

    def functionMove(self):
        if self._oneDMeasurement.isChecked():
            self.oneD = 1
            print("1D measurement ON")
        else:
            self.oneD = 0
            print("1D measurement OFF")

        self.inputData = [
            self._M1FROMValue.text(),
            self._M1TOValue.text(),
            self._M1STEPValue.text(),
            self._M2FROMValue.text(),
            self._M2TOValue.text(),
            self._M2STEPValue.text(),
            self._M3FROMValue.text(),
            self._M3TOValue.text(),
            self._M3STEPValue.text(),
            self._MESPOINTSValue.text(),
            self.oneD,
        ]
        print("Data(functionMove): ", self.inputData)
        self.myworkermove = WorkerMove(self.inputData)
        self.myworkermove.finished.connect(
            self.updateLayoutAfterFinishedMove
        )  # propojeni signalu
        self.myworkermove.on_progress.connect(
            self.updateProgressBar
        )  # propojeni signalu

        self.myworkermove.on_progress2.connect(
            self.updateProgressBarLabel
        )  # propojeni signalu

        print("Run Move Function")

        self._startMeasurement.setEnabled(False)
        self._Home1.setEnabled(False)
        self._Home2.setEnabled(False)
        self._Home3.setEnabled(False)

        self.myworkermove.start()


# Threads for moving the motors:
class HomingThread(QThread):
    on_progress = Signal(int)
    controller = surface_scattering_backend_v1.BSC203ThreeChannelBenchtopStepperMotorController

    def __init__(self, motorID):
        super().__init__()
        self.controller.connect()
        self._active_motor = self.controller.motors[motorID]

    def run(self):
        self._active_motor.home()
        print("Homing done.")


if __name__ == '__main__':
    # Create the Qt Application
    app = QApplication([])
    window = Window()
    window.show()
    sys.exit(app.exec())
