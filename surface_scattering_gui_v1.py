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
from surface_scattering_backend_v1 import WorkerMove


print("Library import done.")

controller = surface_scattering_backend_v1.BSC203ThreeChannelBenchtopStepperMotorController


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
        self._inputData = []
        self._oneD = 0

        # Thread variables
        self.worker = None

        # Labels
        _labelMotorSetupTitle = self._label("Motors Setup:")

        _labelM1from = self._label("From")
        _labelM1to = self._label("To")
        _labelM1step = self._label("Step")
        _labelM1 = self._label("Motor 1")

        _labelM2from = self._label("From")
        _labelM2to = self._label("To")
        _labelM2step = self._label("Step")
        _labelM2 = self._label("Motor 2")

        _labelM3from = self._label("From")
        _labelM3to = self._label("To")
        _labelM3step = self._label("Step")
        _labelM3 = self._label("Motor 3")

        _labelMeasurementSetupTitle = self._label("Measurement Setup:")

        _labelMeasurementNum = self._label("N Measurement points")
        _labelMeasurementN = self._label("[n]")

        _labelHomeTitle = self._label("Homing:")

        _labelTimeToFinishTitle = self._label("Time to Finish:")
        self._labelTimeToFinishValue = self._label("0d 0h 0m 0s")

        _urlLabel = self._label(
            f"<a href='https://www.numsolution.cz/'>https://www.numsolution.cz/</a>"
        )
        _urlLabel.setOpenExternalLinks(True)

        # Line edits
        self._M1FROMValue = self._line_edit("0")
        self._M1TOValue = self._line_edit("90")
        self._M1STEPValue = self._line_edit("30")

        self._M2FROMValue = self._line_edit("90")
        self._M2TOValue = self._line_edit("180")
        self._M2STEPValue = self._line_edit("30")

        self._M3FROMValue = self._line_edit("0")
        self._M3TOValue = self._line_edit("90")
        self._M3STEPValue = self._line_edit("30")

        self._MESPOINTSValue = self._line_edit("500")

        # Buttons
        self._startMeasurement = self._push_button("Start Measurement")
        self._Home1 = self._push_button("Motor 1 Home")
        self._Home2 = self._push_button("Motor 2 Home")
        self._Home3 = self._push_button("Motor 3 Home")
        self._move_1_to = self._push_button("Move 1 to")
        self._scan = self._push_button("Scan")

        self._startMeasurement.clicked.connect(lambda: self.functionMove())

        self._Home1.clicked.connect(lambda: self.start_homing(1))
        self._Home2.clicked.connect(lambda: self.start_homing(2))
        self._Home3.clicked.connect(lambda: self.start_homing(3))
        self._move_1_to.clicked.connect(lambda: self.move_to(1, float(self._M1TOValue.text())))

        self._scan.clicked.connect(lambda: self.start_scanning())

        # Progress bar
        self._progressBar = self._progress_bar(0)

        # Checkbox
        self._oneDMeasurement = QCheckBox("1D Measurement", self)
        self._oneDMeasurement.setChecked(False)
        self._oneDMeasurement.clicked.connect(self._disable_value_editing)

        # Logo
        logo = self._create_logo()

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
        self._layout.addWidget(self._scan, 15, 3, 1, 1)
        self._layout.addWidget(self._Home1, 13, 1, 1, 1)
        self._layout.addWidget(self._Home2, 14, 1, 1, 1)
        self._layout.addWidget(self._Home3, 15, 1, 1, 1)
        self._layout.addWidget(self._move_1_to, 13, 2, 1, 1)
        self._layout.addWidget(self._progressBar, 13, 3, 1, 2)
        self._layout.addWidget(_urlLabel, 17, 4, 1, 1)
        self._layout.addWidget(logo, 0, 4, 1, 2)
        self._layout.addWidget(self._oneDMeasurement, 11, 4, 1, 1)

    # --------- Functions to make creating widgets easier ----------------
    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel()
        label.setText(text)
        return label

    @staticmethod
    def _line_edit(text: str) -> QLineEdit:
        line_edit = QLineEdit()
        line_edit.setText(text)
        return line_edit

    @staticmethod
    def _push_button(text: str) -> QPushButton:
        push_button = QPushButton()
        push_button.setText(text)
        return push_button

    @staticmethod
    def _progress_bar(num: int) -> QProgressBar:
        progress_bar = QProgressBar()
        progress_bar.setValue(num)
        return progress_bar

    # -----------------------------------------------------------------------

    @staticmethod
    def _create_logo():
        logo_png = QPixmap("NUMlogo_200x93.png")
        logo_png = logo_png.scaledToWidth(100, Qt.TransformationMode.SmoothTransformation)
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignRight)
        logo.setPixmap(logo_png)
        return logo

    def _disable_value_editing(self):
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

    def _update_layout_after_finished_scanning(self):
        self._progressBar.setValue(0)
        self._startMeasurement.setEnabled(True)
        self._Home1.setEnabled(True)
        self._Home2.setEnabled(True)
        self._Home3.setEnabled(True)

    @staticmethod
    def _days_hours_minutes_seconds(dt):
        return (
            dt.days,  # days
            dt.seconds // 3600,  # hours
            (dt.seconds // 60) % 60,  # minutes
            dt.seconds
            - ((dt.seconds // 3600) * 3600)
            - ((dt.seconds % 3600 // 60) * 60),
            # seconds
        )

    def _update_progress_bar(self, n):
        self._progressBar.setValue(n)
        print("Progress num:", n)

    def _update_progress_bar_label(self, dm: float):
        delta = timedelta(seconds=dm)
        (days, hours, minutes, seconds) = self._days_hours_minutes_seconds(delta)
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

    def start_homing(self, motor_id):
        self.worker = HomingThread(motor_id)
        self.worker.finished.connect(self._update_layout_after_finished_scanning)  # propojeni signalu
        self.worker.on_progress.connect(self._update_progress_bar)  # propojeni signalu

        print("Activated motor:", motor_id)
        self._startMeasurement.setEnabled(False)
        self._Home1.setEnabled(False)
        self._Home2.setEnabled(False)
        self._Home3.setEnabled(False)

        self.worker.start()

    def move_to(self, motor_id, position):
        self.worker = MovingThread(motor_id, position)
        self.worker.finished.connect(self._update_layout_after_finished_scanning)  # propojeni signalu
        self.worker.on_progress.connect(self._update_progress_bar)  # propojeni signalu

        print("Activated motor:", motor_id)
        self._startMeasurement.setEnabled(False)
        self._Home1.setEnabled(False)
        self._Home2.setEnabled(False)
        self._Home3.setEnabled(False)

        self.worker.start()

    def start_scanning(self):
        if self._oneDMeasurement.isChecked():
            self._oneD = 1
            print("1D measurement ON")
        else:
            self._oneD = 0
            print("1D measurement OFF")

        self._inputData = [
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
            self._oneD]

        print("Input Data: ", self._inputData)
        self.worker = ScanningThread(self._inputData)
        self.worker.finished.connect(self._update_layout_after_finished_scanning)  # propojeni signalu
        self.worker.on_progress.connect(self._update_progress_bar)  # propojeni signalu
        self.worker.on_progress2.connect(self._update_progress_bar_label)  # propojeni signalu

        self._startMeasurement.setEnabled(False)
        self._Home1.setEnabled(False)
        self._Home2.setEnabled(False)
        self._Home3.setEnabled(False)
        self._scan.setEnabled(False)

        self.worker.start()

    def functionMove(self):
        if self._oneDMeasurement.isChecked():
            self._oneD = 1
            print("1D measurement ON")
        else:
            self._oneD = 0
            print("1D measurement OFF")

        self._inputData = [
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
            self._oneD,
        ]
        print("Data(functionMove): ", self._inputData)
        self.myworkermove = WorkerMove(self._inputData)
        self.myworkermove.finished.connect(
            self._update_layout_after_finished_scanning
        )  # propojeni signalu
        self.myworkermove.on_progress.connect(
            self._update_progress_bar
        )  # propojeni signalu

        self.myworkermove.on_progress2.connect(
            self._update_progress_bar_label
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

    def __init__(self, motor_id):
        super().__init__()
        self.controller.connect()
        self._active_motor = self.controller.motors[motor_id]

    def run(self) -> None:
        self._active_motor.home()
        self.controller.connectedController.disconnect()
        print("Controller disconnected.")


class MovingThread(QThread):
    on_progress = Signal(int)

    def __init__(self, motor_id, position):
        super().__init__()
        self._position = position
        controller.connect()
        self._active_motor = controller.motors[motor_id]

    def run(self) -> None:
        self._active_motor.move_to_position(self._position)
        controller.connectedController.disconnect()
        print("Controller disconnected.")


class ScanningThread(QThread):
    on_progress = Signal(int)
    on_progress2 = Signal(float)
    controller = surface_scattering_backend_v1.BSC203ThreeChannelBenchtopStepperMotorController

    def __init__(self, input_data):
        super().__init__()
        self.input_data = input_data
        self.controller.connect()

    def run(self) -> None:
        if self.input_data[10] == 1:
            print("1D scanning.")
            self.controller.scanning_1d(self.input_data, self.on_progress, self.on_progress2)
        else:
            print("3D scanning.")
            self.controller.scanning_3d(self.input_data, self.on_progress, self.on_progress2)
        self.controller.connectedController.disconnect()
        print("Controller disconnected.")


if __name__ == '__main__':
    # Create the Qt Application
    app = QApplication([])
    window = Window()
    window.show()
    sys.exit(app.exec())
