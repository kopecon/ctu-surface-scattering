# GUI libraries
from PySide6.QtGui import QPixmap, QKeyEvent
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

# System libraries
import sys
from datetime import timedelta

# Custom modules:
import surface_scattering_backend_v1

print("Library import done.")

"""
The surface scattering measuring project consists of 3 files:

    surface_scattering_gui.py: The main file that is meant to be executed. Builds a GUI to interact with the lab
        measurement device.

    surface_scattering_backend.py: Provides access and control of the hardware.  
    
    surface_scattering_scan.py: Provides the scan calculations and output file storing

Hardware:
    Controller: 
        BSC203 - Three-Channel Benchtop Stepper Motor Controller 
        Link - https://www.thorlabs.com/thorproduct.cfm?partnumber=BSC203
    Motors: 
        HDR50 - Heavy-Duty Rotation Stage with Stepper Motor
        Link - https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=1064

Dependent Software:
    "Thorlabs Kinesis" needs to be installed on the device which is to be executing this python script.
    Correct motors have to be set up in the Thorlabs Kinesis user interface.
    Kinesis user interface has to be closed while this program is running, or the controller fails to connect.
"""

controller = surface_scattering_backend_v1.BSC203ThreeChannelBenchtopStepperMotorController


def days_hours_minutes_seconds(dt):
    # TODO: Refactor this into more readable code
    return (
        dt.days,  # days
        dt.seconds // 3600,  # hours
        (dt.seconds // 60) % 60,  # minutes
        dt.seconds - ((dt.seconds // 3600) * 3600) - ((dt.seconds % 3600 // 60) * 60)  # seconds
    )


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        # Window setup
        _central_widget = QWidget()
        self.setCentralWidget(_central_widget)
        self._layout = QGridLayout()
        _central_widget.setLayout(self._layout)

        self.setWindowTitle("Surface Scattering Measurement")
        self.setFixedSize(QSize(600, 600))

        # Measurement arguments:
        self._input_data = []
        self._scan_1d = False
        self._scan_3d = False

        # Thread variables
        self.workers = []

        # Labels
        _label_motor_setup_title = self._label("Motors Setup:")

        _label_m1_from = self._label("From")
        _label_m1_to = self._label("To")
        _label_m1_step = self._label("Step")
        _label_m1 = self._label("Motor 1")

        _label_m2_from = self._label("From")
        _label_m2_to = self._label("To")
        _label_m2_step = self._label("Step")
        _label_m2 = self._label("Motor 2")

        _label_m3_from = self._label("From")
        _label_m3_to = self._label("To")
        _label_m3_step = self._label("Step")
        _label_m3 = self._label("Motor 3")

        _label_measurement_setup_title = self._label("Measurement Setup:")

        _label_measurement_num = self._label("Measurement points")
        _label_measurement_n = self._label("[n]")
        _label_scan_type = self._label("Scan type:")

        _label_home_title = self._label("Homing:")

        _label_time_to_finish_title = self._label("Time to Finish:")
        self._label_time_to_finish_value = self._label("0d 0h 0m 0s")

        _label_url = self._label(
            f"<a href='https://www.numsolution.cz/'>https://www.numsolution.cz/</a>"
        )
        _label_url.setOpenExternalLinks(True)

        # Line edits
        self._m1_from_value = self._line_edit("0")
        self._m1_to_value = self._line_edit("90")
        self._m1_step_value = self._line_edit("30")

        self._m2_from_value = self._line_edit("90")
        self._m2_to_value = self._line_edit("180")
        self._m2_step_value = self._line_edit("30")

        self._m3_from_value = self._line_edit("0")
        self._m3_to_value = self._line_edit("90")
        self._m3_step_value = self._line_edit("30")

        self._number_of_measurement_points_value = self._line_edit("500")

        # Buttons
        self._home1 = self._push_button("Motor 1 Home")
        self._home2 = self._push_button("Motor 2 Home")
        self._home3 = self._push_button("Motor 3 Home")
        self._home_all = self._push_button("Motor All")
        self._move_1_to = self._push_button("Move")
        self._move_2_to = self._push_button("Move")
        self._move_3_to = self._push_button("Move")
        self._scan = self._push_button("Scan")
        self._stop = self._push_button("STOP")
        self._connection_button = self._push_button("Connect")

        self._home1.clicked.connect(lambda: self.start_homing(1))
        self._home2.clicked.connect(lambda: self.start_homing(2))
        self._home3.clicked.connect(lambda: self.start_homing(3))
        self._home_all.clicked.connect(lambda: self.start_homing(1))
        self._home_all.clicked.connect(lambda: self.start_homing(2))
        self._home_all.clicked.connect(lambda: self.start_homing(3))
        self._move_1_to.clicked.connect(lambda: self.move_to(1, float(self._m1_to_value.text())))
        self._move_2_to.clicked.connect(lambda: self.move_to(2, float(self._m2_to_value.text())))
        self._move_3_to.clicked.connect(lambda: self.move_to(3, float(self._m3_to_value.text())))
        self._stop.clicked.connect(lambda: self.stop_motors())
        self._scan.clicked.connect(lambda: self.start_scanning())
        self._connection_button.clicked.connect(lambda: self.connect_devices())

        # Progress bar
        self._progress_bar = self._progress_bar(0)

        # Checkbox
        self._measurement_1d = QCheckBox("1D Measurement", self)
        self._measurement_3d = QCheckBox("3D Measurement", self)
        self._measurement_1d.setChecked(False)
        self._measurement_3d.setChecked(True)
        self._measurement_3d.setEnabled(False)
        self._measurement_1d.clicked.connect(self._restrict_value_editing_for_1d_measurement)
        self._measurement_3d.clicked.connect(self._restrict_value_editing_for_3d_measurement)

        # Logo
        logo = self._create_logo()

        # Place and display created widgets
        self._layout.addWidget(_label_motor_setup_title, 0, 0, 1, 1)
        self._layout.addWidget(_label_m1_from, 1, 1, 1, 1)
        self._layout.addWidget(_label_m1_to, 1, 2, 1, 1)
        self._layout.addWidget(_label_m1_step, 1, 3, 1, 1)
        self._layout.addWidget(_label_m1, 2, 0, 1, 1)
        self._layout.addWidget(_label_m2_from, 3, 1, 1, 1)
        self._layout.addWidget(_label_m2_to, 3, 2, 1, 1)
        self._layout.addWidget(_label_m2_step, 3, 3, 1, 1)
        self._layout.addWidget(_label_m2, 4, 0, 1, 1)
        self._layout.addWidget(_label_m3_from, 5, 1, 1, 1)
        self._layout.addWidget(_label_m3_to, 5, 2, 1, 1)
        self._layout.addWidget(_label_m3_step, 5, 3, 1, 1)
        self._layout.addWidget(_label_m3, 6, 0, 1, 1)
        self._layout.addWidget(_label_measurement_setup_title, 7, 0, 1, 1)
        self._layout.addWidget(_label_measurement_num, 8, 1, 1, 1)
        self._layout.addWidget(_label_measurement_n, 8, 3, 1, 1)
        self._layout.addWidget(_label_scan_type, 9, 1, 1, 1)
        self._layout.addWidget(_label_home_title, 13, 0, 1, 1)
        self._layout.addWidget(_label_time_to_finish_title, 11, 1, 1, 1)
        self._layout.addWidget(self._label_time_to_finish_value, 11, 2, 1, 1)
        self._layout.addWidget(self._m1_from_value, 2, 1, 1, 1)
        self._layout.addWidget(self._m1_to_value, 2, 2, 1, 1)
        self._layout.addWidget(self._m1_step_value, 2, 3, 1, 1)
        self._layout.addWidget(self._m2_from_value, 4, 1, 1, 1)
        self._layout.addWidget(self._m2_to_value, 4, 2, 1, 1)
        self._layout.addWidget(self._m2_step_value, 4, 3, 1, 1)
        self._layout.addWidget(self._m3_from_value, 6, 1, 1, 1)
        self._layout.addWidget(self._m3_to_value, 6, 2, 1, 1)
        self._layout.addWidget(self._m3_step_value, 6, 3, 1, 1)
        self._layout.addWidget(self._number_of_measurement_points_value, 8, 2, 1, 1)
        self._layout.addWidget(self._scan, 10, 1, 1, 3)
        self._layout.addWidget(self._connection_button, 0, 1, 1, 1)
        self._layout.addWidget(self._home1, 14, 1, 1, 1)
        self._layout.addWidget(self._home2, 14, 2, 1, 1)
        self._layout.addWidget(self._home3, 14, 3, 1, 1)
        self._layout.addWidget(self._home_all, 15, 2, 1, 1)
        self._layout.addWidget(self._move_1_to, 2, 4, 1, 1)
        self._layout.addWidget(self._move_2_to, 4, 4, 1, 1)
        self._layout.addWidget(self._move_3_to, 6, 4, 1, 1)
        self._layout.addWidget(self._stop, 0, 3, 1, 1)
        self._layout.addWidget(self._progress_bar, 12, 1, 1, 3)
        self._layout.addWidget(_label_url, 16, 3, 1, 2)
        self._layout.addWidget(logo, 0, 4, 1, 2)
        self._layout.addWidget(self._measurement_1d, 9, 2, 1, 1)
        self._layout.addWidget(self._measurement_3d, 9, 3, 1, 1)

        self._connect_on_start()  # Try connecting to the measurement device

    # ----------------------------------------------------------------------    Wrappers to make creating widgets easier
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

    @staticmethod
    def _create_logo():
        logo_png = QPixmap("NUMlogo_200x93.png")
        logo_png = logo_png.scaledToWidth(100, Qt.TransformationMode.SmoothTransformation)
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignRight)
        logo.setPixmap(logo_png)
        return logo

    # -----------------------------------------------------------------------------------------------    Widget handling
    def _restrict_value_editing_for_1d_measurement(self):
        self._measurement_1d.setEnabled(False)
        self._measurement_3d.setEnabled(True)
        self._measurement_3d.setChecked(False)

        if self._measurement_1d.isChecked():
            self._m1_to_value.setEnabled(False)
            self._m1_step_value.setEnabled(False)
            self._m2_to_value.setEnabled(False)
            self._m2_step_value.setEnabled(False)
            self._m3_from_value.setEnabled(False)
            self._m3_to_value.setEnabled(False)

        else:
            self._m1_to_value.setEnabled(True)
            self._m1_step_value.setEnabled(True)
            self._m2_to_value.setEnabled(True)
            self._m2_step_value.setEnabled(True)
            self._m3_from_value.setEnabled(True)
            self._m3_to_value.setEnabled(True)

    def _restrict_value_editing_for_3d_measurement(self):
        # Enable every widget
        widgets = self.get_window_widgets()
        for widget in widgets:
            if hasattr(widget, 'setEnabled'):
                widget.setEnabled(True)

        self._measurement_3d.setEnabled(False)
        self._measurement_1d.setEnabled(True)
        self._measurement_1d.setChecked(False)

    def _update_layout_after_finished_scanning(self):
        self._progress_bar.setValue(0)
        # Enable every widget
        widgets = self.get_window_widgets()
        for widget in widgets:
            if hasattr(widget, 'setEnabled'):
                widget.setEnabled(True)

        self._measurement_1d.setEnabled(True)
        self._measurement_1d.setChecked(False)
        self._measurement_3d.setEnabled(False)
        self._measurement_3d.setChecked(True)

    def _update_progress_bar(self, n):
        self._progress_bar.setValue(n)
        print("Progress num:", n)

    def _update_progress_bar_label(self, dm: float):
        delta = timedelta(seconds=dm)
        (days, hours, minutes, seconds) = days_hours_minutes_seconds(delta)
        n = (str(days)
             + "d "
             + str(hours)
             + "h "
             + str(minutes)
             + "m "
             + str(seconds)
             + "s")
        self._label_time_to_finish_value.setText(n)

    def get_window_widgets(self):
        all_window_widgets = []
        for i in range(self._layout.count()):
            widget = self._layout.itemAt(i).widget()
            all_window_widgets.append(widget)
        return all_window_widgets

    def keyPressEvent(self, event):
        # For safety reasons, if any motor is moving and any key is pressed, all the motors stop.
        # Does not work with "SpaceBar" key.
        if isinstance(event, QKeyEvent) and any(worker.isRunning() for worker in self.workers):
            self.stop_motors()

    #  ---------------------------------------------------------------------------------------    Motor moving functions
    def start_homing(self, motor_id):
        worker = HomingThread(motor_id)
        self.workers.append(worker)
        print("Activated motor:", motor_id)

        worker.start()

    def move_to(self, motor_id, position):
        worker = MovingThread(motor_id, position)
        self.workers.append(worker)  # Associating the worker with the object prevents crashing
        print("Activated motor:", motor_id)

        worker.start()

    def start_scanning(self):
        if self._measurement_1d.isChecked():
            self._scan_1d = True
            self._scan_3d = False
            print("1D measurement ON")
        elif self._measurement_3d.isChecked():
            self._scan_3d = False
            self._scan_3d = True
            print("3D measurement ON")

        self._input_data = [
            self._m1_from_value.text(),
            self._m1_to_value.text(),
            self._m1_step_value.text(),
            self._m2_from_value.text(),
            self._m2_to_value.text(),
            self._m2_step_value.text(),
            self._m3_from_value.text(),
            self._m3_to_value.text(),
            self._m3_step_value.text(),
            self._number_of_measurement_points_value.text(),
            self._scan_1d]

        print("Input Data: ", self._input_data)
        worker = ScanningThread(self._scan_1d, self._scan_3d, self._input_data)
        self.workers.append(worker)
        worker.finished.connect(self._update_layout_after_finished_scanning)  # propojeni signalu
        worker.on_progress.connect(self._update_progress_bar)  # propojeni signalu
        worker.on_progress2.connect(self._update_progress_bar_label)  # propojeni signalu

        self._home1.setEnabled(False)
        self._home2.setEnabled(False)
        self._home3.setEnabled(False)
        self._scan.setEnabled(False)

        worker.start()

    @staticmethod
    def stop_motors():
        controller.stop_motors()

    def connect_devices(self):
        if self._connection_button.text() == "Connect":
            connection_check = controller.connect()  # Connects to the controller and returns 0 if connected correctly
            if connection_check == 1:
                # Not connected (Error)
                return 1
            elif connection_check == 0:
                widgets = self.get_window_widgets()
                for widget in widgets:
                    if hasattr(widget, 'setEnabled'):
                        widget.setEnabled(True)
                self._connection_button.setText("Disconnect")
        elif self._connection_button.text() == "Disconnect":
            controller.disconnect()
            self._connection_button.setText("Connect")
            # Disable buttons
            widgets = self.get_window_widgets()
            for widget in widgets:
                if hasattr(widget, 'setEnabled'):
                    if isinstance(widget, QPushButton) and widget.text() != 'Connect':
                        widget.setEnabled(False)

    def _connect_on_start(self):
        widgets = self.get_window_widgets()
        for widget in widgets:
            if hasattr(widget, 'setEnabled'):
                if isinstance(widget, QPushButton) and widget.text() != 'Connect':
                    widget.setEnabled(False)

        self.connect_devices()


# Threads for moving the motors:
class HomingThread(QThread):
    on_progress = Signal(int)

    def __init__(self, motor_id):
        super().__init__()
        self._active_motor = controller.motors[motor_id]

    def run(self) -> None:
        self._active_motor.home(velocity=10)


class MovingThread(QThread):
    on_progress = Signal(int)

    def __init__(self, motor_id, position):
        super().__init__()
        self._position = position
        self._active_motor = controller.motors[motor_id]

    def run(self) -> None:
        self._active_motor.move_to_position(self._position)


class ScanningThread(QThread):
    on_progress = Signal(int)
    on_progress2 = Signal(float)

    def __init__(self, scan_1d, scan_3d, input_data):
        super().__init__()
        self.scan_1d = scan_1d
        self.scan_3d = scan_3d
        self.input_data = input_data

    def run(self) -> None:
        if self.scan_1d:
            print("1D scanning.")
            controller.scanning_1d(self.input_data, self.on_progress, self.on_progress2)
        elif self.scan_3d:
            print("3D scanning.")
            controller.scanning_3d(self.input_data, self.on_progress, self.on_progress2)


if __name__ == '__main__':
    # Create the Qt Application
    app = QApplication([])
    window = Window()
    window.show()
    window_termination = app.exec()
    controller.disconnect()
    sys.exit(window_termination)
