# System libraries
import sys
from datetime import timedelta

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
    QCheckBox, QFrame,
)

# TODO: Add function: Dynamic range calibration, graphing.

# Custom modules:
import _backend
import _real_time_graph

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

controller = _backend.BSC203ThreeChannelBenchtopStepperMotorController


def days_hours_minutes_seconds(dt):
    days = dt.days
    hours = dt.seconds // 3600
    minutes = (dt.seconds // 60) % 60
    seconds = dt.seconds - ((dt.seconds // 3600) * 3600) - ((dt.seconds % 3600 // 60) * 60)
    return days, hours, minutes, seconds


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        # Window setup
        _central_widget = QWidget()
        self.setCentralWidget(_central_widget)
        self._layout = QGridLayout()
        _central_widget.setLayout(self._layout)

        self.setWindowTitle("Surface Scattering Measurement")
        self.setFixedSize(QSize(640, 600))

        # Measurement arguments:
        self.sensor_real_time_graph = _real_time_graph.GraphWindow(controller)
        self._input_data = []
        self._scan_1d = False
        self._scan_3d = False

        # Thread variables
        self.workers = []

        # Labels
        _label_controller_setup_title = self._label("Controller:")
        _label_motor_setup_title = self._label("Motors:")

        self._label_m1_from = self._label("From")  # Text is being changed => self.
        _label_m1_to = self._label("To")
        _label_m1_step = self._label("Step")
        _label_m1_position = self._label("Position")
        _label_m1 = self._label("Motor 1")
        _label_m1.setStyleSheet("qproperty-alignment: AlignRight;")

        self._label_m2_from = self._label("From")
        _label_m2_to = self._label("To")
        _label_m2_step = self._label("Step")
        _label_m2_position = self._label("Position")
        _label_m2 = self._label("Motor 2")
        _label_m2.setStyleSheet("qproperty-alignment: AlignRight;")

        _label_m3_from = self._label("From")
        _label_m3_to = self._label("To")
        _label_m3_step = self._label("Step")
        _label_m3_position = self._label("Position")
        _label_m3 = self._label("Motor 3")
        _label_m3.setStyleSheet("qproperty-alignment: AlignRight;")

        _label_calibration_title = self._label("Calibration:")
        _label_calibration_m1 = self._label("Motor 1")
        _label_calibration_m2 = self._label("Motor 2")
        _label_calibration_m3 = self._label("Motor 3")
        _label_calibration_where = self._label("Where")
        _label_calibration_m3_range = self._label("Range")

        _label_measurement_setup_title = self._label("Measurement:")

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
        self._m1_move_to_value = self._line_edit("0")

        self._m2_from_value = self._line_edit("90")
        self._m2_to_value = self._line_edit("180")
        self._m2_step_value = self._line_edit("30")
        self._m2_move_to_value = self._line_edit("0")

        self._m3_from_value = self._line_edit("0")
        self._m3_to_value = self._line_edit("90")
        self._m3_step_value = self._line_edit("30")
        self._m3_move_to_value = self._line_edit("0")

        self._calibration_m1_value = self._line_edit("80")
        self._calibration_m2_value = self._line_edit("90")
        self._calibration_m3_value = self._line_edit("80")
        self._calibration_m3_range_value = self._line_edit("10")

        self._number_of_measurement_points_value = self._line_edit("500")

        # Buttons
        self._home1 = self._push_button("Motor 1 Home")
        self._home2 = self._push_button("Motor 2 Home")
        self._home3 = self._push_button("Motor 3 Home")
        self._home_all = self._push_button("Motor All")
        self._move_1_to = self._push_button("Move")
        self._move_2_to = self._push_button("Move")
        self._move_3_to = self._push_button("Move")
        self._calibrate = self._push_button("Calibrate")
        self._scan = self._push_button("Scan")
        self._view_scattering_graph = self._push_button("Graph")
        self._stop = self._push_button("STOP")
        self._stop.setFixedSize(80, 80)
        self._stop.setStyleSheet("QPushButton {background-color: rgb(255, 26, 26); color: white;}")
        self._connection_button = self._push_button("Connect")

        self._home1.clicked.connect(lambda: self.start_homing(1))
        self._home2.clicked.connect(lambda: self.start_homing(2))
        self._home3.clicked.connect(lambda: self.start_homing(3))
        self._home_all.clicked.connect(lambda: self.start_homing(1))
        self._home_all.clicked.connect(lambda: self.start_homing(2))
        self._home_all.clicked.connect(lambda: self.start_homing(3))
        self._move_1_to.clicked.connect(lambda: self.move_to(1, float(self._m1_move_to_value.text())))
        self._move_2_to.clicked.connect(lambda: self.move_to(2, float(self._m2_move_to_value.text())))
        self._move_3_to.clicked.connect(lambda: self.move_to(3, float(self._m3_move_to_value.text())))
        self._stop.clicked.connect(lambda: self.stop_motors())
        self._calibrate.clicked.connect(lambda: self.start_calibration([self._calibration_m1_value.text(),
                                                                        self._calibration_m2_value.text(),
                                                                        self._calibration_m3_value.text(),
                                                                        self._calibration_m3_range_value.text()]))
        self._scan.clicked.connect(lambda: self.start_scanning())
        self._view_scattering_graph.clicked.connect(lambda: self.toggle_scattering_graph_visibility())
        self._connection_button.clicked.connect(lambda: self.connect_or_disconnect_devices())

        # Progress bar
        self._progress_bar = self._progress_bar(0)

        # Checkbox
        self._measurement_1d = QCheckBox("1D", self)
        self._measurement_3d = QCheckBox("3D", self)
        self._measurement_1d.setChecked(False)
        self._measurement_3d.setChecked(True)
        self._measurement_3d.setEnabled(False)
        self._measurement_1d.clicked.connect(self._restrict_value_editing_for_1d_scan)
        self._measurement_3d.clicked.connect(self._restrict_value_editing_for_3d_scan)

        # Logo
        logo = self._create_logo()  # Currently unused

        # Place and display created widgets
        self._layout.addWidget(self._connection_button, 0, 2, 1, 1)
        self._layout.addWidget(_label_url, 0, 6, 1, 3)
        self._layout.addWidget(_label_controller_setup_title, 0, 0, 1, 2)
        self._layout.addWidget(QHLine(), 1, 0, 1, self._layout.columnCount())
        self._layout.addWidget(_label_motor_setup_title, 2, 0, 1, 1)
        self._layout.addWidget(self._label_m1_from, 3, 2, 1, 1)
        self._layout.addWidget(_label_m1_to, 3, 3, 1, 1)
        self._layout.addWidget(_label_m1_step, 3, 4, 1, 1)
        self._layout.addWidget(_label_m1_position, 3, 6, 1, 1)
        self._layout.addWidget(_label_m1, 4, 1, 1, 1)
        self._layout.addWidget(self._m1_from_value, 4, 2, 1, 1)
        self._layout.addWidget(self._m1_to_value, 4, 3, 1, 1)
        self._layout.addWidget(self._m1_step_value, 4, 4, 1, 1)
        self._layout.addWidget(QVLine(), 4, 5, 1, 1)
        self._layout.addWidget(self._m1_move_to_value, 4, 6, 1, 1)
        self._layout.addWidget(self._move_1_to, 4, 7, 1, 1)
        self._layout.addWidget(self._label_m2_from, 5, 2, 1, 1)
        self._layout.addWidget(_label_m2_to, 5, 3, 1, 1)
        self._layout.addWidget(_label_m2_step, 5, 4, 1, 1)
        self._layout.addWidget(_label_m2_position, 5, 6, 1, 1)
        self._layout.addWidget(_label_m2, 6, 1, 1, 1)
        self._layout.addWidget(self._m2_from_value, 6, 2, 1, 1)
        self._layout.addWidget(self._m2_to_value, 6, 3, 1, 1)
        self._layout.addWidget(self._m2_step_value, 6, 4, 1, 1)
        self._layout.addWidget(QVLine(), 6, 5, 1, 1)
        self._layout.addWidget(self._m2_move_to_value, 6, 6, 1, 1)
        self._layout.addWidget(self._move_2_to, 6, 7, 1, 1)
        self._layout.addWidget(_label_m3_from, 7, 2, 1, 1)
        self._layout.addWidget(_label_m3_to, 7, 3, 1, 1)
        self._layout.addWidget(_label_m3_step, 7, 4, 1, 1)
        self._layout.addWidget(_label_m3_position, 7, 6, 1, 1)
        self._layout.addWidget(_label_m3, 8, 1, 1, 1)
        self._layout.addWidget(self._m3_from_value, 8, 2, 1, 1)
        self._layout.addWidget(self._m3_to_value, 8, 3, 1, 1)
        self._layout.addWidget(self._m3_step_value, 8, 4, 1, 1)
        self._layout.addWidget(QVLine(), 8, 5, 1, 1)
        self._layout.addWidget(self._m3_move_to_value, 8, 6, 1, 1)
        self._layout.addWidget(self._move_3_to, 8, 7, 1, 1)
        self._layout.addWidget(QHLine(), 9, 0, 1, self._layout.columnCount())
        self._layout.addWidget(_label_calibration_title, 10, 0, 1, 1)
        self._layout.addWidget(_label_calibration_m1, 11, 2, 1, 1)
        self._layout.addWidget(_label_calibration_m2, 11, 3, 1, 1)
        self._layout.addWidget(_label_calibration_m3, 11, 4, 1, 1)
        self._layout.addWidget(QVLine(), 12, 5, 1, 1)
        self._layout.addWidget(_label_calibration_m3_range, 11, 6, 1, 1)
        self._layout.addWidget(_label_calibration_where, 12, 1, 1, 1)
        self._layout.addWidget(self._calibration_m1_value, 12, 2, 1, 1)
        self._layout.addWidget(self._calibration_m2_value, 12, 3, 1, 1)
        self._layout.addWidget(self._calibration_m3_value, 12, 4, 1, 1)
        self._layout.addWidget(self._calibration_m3_range_value, 12, 6, 1, 1)
        self._layout.addWidget(self._calibrate, 12, 7, 1, 1)
        self._layout.addWidget(QHLine(), 14, 0, 1, self._layout.columnCount())
        self._layout.addWidget(_label_measurement_setup_title, 15, 0, 1, 1)
        self._layout.addWidget(_label_measurement_num, 16, 2, 1, 1)
        self._layout.addWidget(self._number_of_measurement_points_value, 16, 3, 1, 1)
        self._layout.addWidget(_label_measurement_n, 16, 4, 1, 1)
        self._layout.addWidget(_label_scan_type, 17, 2, 1, 1)
        self._layout.addWidget(self._measurement_1d, 17, 3, 1, 1)
        self._layout.addWidget(self._measurement_3d, 17, 4, 1, 1)
        self._layout.addWidget(self._scan, 18, 2, 1, 3)
        self._layout.addWidget(self._view_scattering_graph, 18, 6, 1, 2)
        self._layout.addWidget(_label_time_to_finish_title, 19, 2, 1, 1)
        self._layout.addWidget(self._label_time_to_finish_value, 19, 3, 1, 1)
        self._layout.addWidget(self._progress_bar, 20, 2, 1, 3)
        self._layout.addWidget(QHLine(), 21, 0, 1, self._layout.columnCount())
        self._layout.addWidget(_label_home_title, 22, 0, 1, 1)
        self._layout.addWidget(self._stop, 22, 6, 4, 3, alignment=Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._home1, 23, 2, 1, 1)
        self._layout.addWidget(self._home2, 23, 3, 1, 1)
        self._layout.addWidget(self._home3, 23, 4, 1, 1)
        self._layout.addWidget(self._home_all, 24, 3, 1, 1)

        # Perform these tasks at the start of the program
        self._set_disconnected_layout()
        self.connect_or_disconnect_devices()

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
        # This is not doing anything right now
        logo_png = QPixmap("NUMlogo_200x93.png")
        logo_png = logo_png.scaledToWidth(100, Qt.TransformationMode.SmoothTransformation)
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignRight)
        logo.setPixmap(logo_png)
        return logo

    # -----------------------------------------------------------------------------------------------    Widget handling
    def get_window_widgets(self, *widget_types):
        all_window_widgets = []
        for i in range(self._layout.count()):
            widget = self._layout.itemAt(i).widget()
            all_window_widgets.append(widget)
            # If widget type is specified, remove unwanted widgets and return only the requested widget type
            for widget_type in widget_types:
                if not isinstance(widget, widget_type) and widget_type != ():
                    all_window_widgets.remove(widget)
        return all_window_widgets

    def _enable_every_widget(self, *widget_types):
        widgets = self.get_window_widgets(widget_types)
        for widget in widgets:
            if hasattr(widget, 'setEnabled'):
                widget.setEnabled(True)

    def _disable_every_widget(self, *widget_types):
        widgets = self.get_window_widgets(widget_types)
        for widget in widgets:
            if hasattr(widget, 'setEnabled'):
                widget.setEnabled(False)

    def _set_disconnected_layout(self):
        self._disable_every_widget(QPushButton)
        self._stop.setEnabled(True)
        self._connection_button.setEnabled(True)
        self._connection_button.setText("Connect")

    def _set_connected_layout(self):
        self._enable_every_widget(QPushButton)
        self._connection_button.setText("Disconnect")

    def _restrict_value_editing_for_1d_scan(self):
        self._measurement_1d.setEnabled(False)
        self._measurement_3d.setEnabled(True)
        self._measurement_3d.setChecked(False)

        self._m1_to_value.setEnabled(False)
        self._m1_step_value.setEnabled(False)
        self._m2_to_value.setEnabled(False)
        self._m2_step_value.setEnabled(False)
        self._m3_from_value.setEnabled(True)
        self._m3_to_value.setEnabled(True)
        self._label_m1_from.setText("Where")
        self._label_m2_from.setText("Where")
        self._m3_from_value.setText('270')
        self._m3_to_value.setText('90')

    def _restrict_value_editing_for_3d_scan(self):
        # First enable everything
        self._enable_every_widget(QLineEdit)
        # Disable what is needed
        self._measurement_3d.setEnabled(False)
        self._measurement_1d.setEnabled(True)
        self._measurement_1d.setChecked(False)

        self._label_m1_from.setText("From")
        self._label_m2_from.setText("From")
        self._m3_from_value.setText('0')
        self._m3_to_value.setText('90')

    def _reset_layout(self):
        self._progress_bar.setValue(0)

        self._enable_every_widget()

        self._measurement_1d.setChecked(False)
        self._measurement_3d.setChecked(True)
        self._measurement_3d.setEnabled(False)
        self._label_m1_from.setText("From")
        self._label_m2_from.setText("From")
        self._m3_from_value.setText('0')
        self._m3_to_value.setText('90')

    def _update_progress_bar_label(self, finish_time):
        delta = timedelta(seconds=finish_time)
        (days, hours, minutes, seconds) = days_hours_minutes_seconds(delta)
        n = (str(days) + "d " + str(hours) + "h " + str(minutes) + "m " + str(seconds) + "s")
        self._label_time_to_finish_value.setText(n)

    def _update_progress_bar(self, signal: list[int, float]):
        progress = signal[0]
        finish_time = signal[1]
        self._progress_bar.setValue(progress)
        self._update_progress_bar_label(finish_time)

    def keyPressEvent(self, event):
        # For safety reasons, if any motor is moving and any key is pressed, all the motors stop.
        # Does not work with "SpaceBar" key.
        if isinstance(event, QKeyEvent) and any(worker.isRunning() for worker in self.workers):
            self.stop_motors()

    def toggle_scattering_graph_visibility(self):
        if self.sensor_real_time_graph.isVisible():
            self.sensor_real_time_graph.hide()
        else:
            self.sensor_real_time_graph.show()

    #  -----------------------------------------------------------------------------------    Hardware control functions
    def start_calibration(self, input_data):
        worker = CalibratingThread(input_data)
        self.workers.append(worker)

        worker.start()

    def start_homing(self, motor_id):
        home_button = self.__getattribute__(f'_home{motor_id}')
        home_all_button = self._home_all
        worker = HomingThread(motor_id, home_button, home_all_button)
        self.workers.append(worker)
        worker.start()

    def move_to(self, motor_id, position):
        worker = MovingThread(motor_id, position)
        self.workers.append(worker)  # Associating the worker with the object prevents crashing

        worker.start()

    def start_scanning(self):
        if self._measurement_1d.isChecked():
            self._scan_1d = True
            self._scan_3d = False
            print("Scanning 1D...")
        elif self._measurement_3d.isChecked():
            self._scan_1d = False
            self._scan_3d = True
            print("Scanning 3D...")

        if self._scan_3d:
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

        elif self._scan_1d:
            self._input_data = [
                self._m1_from_value.text(),
                self._m1_from_value.text(),
                self._m1_step_value.text(),
                self._m2_from_value.text(),
                self._m2_from_value.text(),
                self._m2_step_value.text(),
                self._m3_from_value.text(),
                self._m3_to_value.text(),
                self._m3_step_value.text(),
                self._number_of_measurement_points_value.text(),
                self._scan_1d,
                self._scan_3d]

        print("Input Data: ", self._input_data)
        worker = ScanningThread(self._input_data)
        self.workers.append(worker)
        worker.finished.connect(self._reset_layout)
        worker.thread_signal.connect(self._update_progress_bar)

        self._disable_every_widget()
        self._stop.setEnabled(True)
        self._view_scattering_graph.setEnabled(True)

        worker.start()

    def stop_motors(self):
        for worker in self.workers:
            worker.termination_request = True
        controller.stop_motors_and_disconnect()
        self._set_disconnected_layout()

    def connect_or_disconnect_devices(self):
        if self._connection_button.text() == "Connect":
            connection_check = controller.connect()  # Connects to the controller and returns 0 if connected correctly
            if connection_check == 1:
                self._set_disconnected_layout()
                # Not connected (Error)
                return 1
            elif connection_check == 0:
                # Connected
                self._set_connected_layout()
        elif self._connection_button.text() == "Disconnect":
            controller.disconnect()
            self._set_disconnected_layout()


class CalibratingThread(QThread):
    def __init__(self, input_data):
        super().__init__()
        self.termination_requested = False
        self.input_data = input_data

    def run(self) -> None:
        if self.termination_requested:
            return  # Stop running this thread if termination is requested
        controller.calibrate(self.input_data)


# Threads for moving the motors:
class HomingThread(QThread):

    def __init__(self, motor_id: int, motor_home_button: QPushButton, motor_home_all_button: QPushButton):
        super().__init__()
        self.termination_requested = False
        self._active_motor = controller.motors[motor_id]
        self.motor_home_button = motor_home_button
        self.motor_home_all_button = motor_home_all_button

    def run(self) -> None:
        if self.termination_requested:
            return  # Stop running this thread if termination is requested
        self.motor_home_button.setEnabled(False)
        self.motor_home_all_button.setEnabled(False)
        self._active_motor.home(velocity=10)
        self.motor_home_button.setEnabled(True)
        self.motor_home_all_button.setEnabled(True)
        return


class MovingThread(QThread):

    def __init__(self, motor_id, position):
        super().__init__()
        self.termination_requested = False
        self._position = position
        self._active_motor = controller.motors[motor_id]

    def run(self) -> None:
        if self.termination_requested:
            return  # Stop running this thread if termination is requested
        self._active_motor.move_to_position(self._position)


class ScanningThread(QThread):
    thread_signal = Signal(list)

    def __init__(self, input_data):
        super().__init__()
        self.termination_requested = False
        self.input_data = input_data

    def run(self) -> None:
        if self.termination_requested:
            return  # Stop running this thread if termination is requested
        controller.scanning(self.input_data, self.thread_signal)


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class QVLine(QFrame):
    def __init__(self):
        super(QVLine, self).__init__()
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setFixedSize(self.frameWidth(), 30)


if __name__ == '__main__':
    # Create the Qt Application
    app = QApplication([])
    window = Window()
    window.show()
    window_termination = app.exec()
    controller.disconnect()
    sys.exit(window_termination)
