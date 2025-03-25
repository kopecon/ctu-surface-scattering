# System libraries
import sys
import time
from datetime import timedelta

# GUI libraries
from PySide6.QtGui import QPixmap, QKeyEvent, QDoubleValidator, QIntValidator
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

# Plotting libraries:
from matplotlib import pyplot as plt

# Custom modules:
import _backend
import _real_time_graphs

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
connection_check = controller.connect()  # Connects to the controller and returns 0 if connected hardware, 1 if virtual.

# Set initial values for motor positions predefined in the GUI
controller.motor_1.scan_from = float(0)
controller.motor_1.scan_to = float(90)
controller.motor_1.scan_step = float(30)

controller.motor_2.scan_from = float(90)
controller.motor_2.scan_to = float(180)
controller.motor_2.scan_step = float(30)

controller.motor_3.scan_from = float(0)
controller.motor_3.scan_to = float(90)
controller.motor_3.scan_step = float(30)


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
        self.graph_2d = _real_time_graphs.Graph2D()
        self.graph_3d = _real_time_graphs.Graph3D()
        self._input_data = []
        self._scan_1d = False
        self._scan_3d = False

        # Thread variables
        self.workers = []

        # Labels
        _controller_setup_title_label = self._label("Controller:")
        _motor_setup_title_label = self._label("Motors:")

        self._m1_from_label = self._label("From")  # Text is being changed => self.
        _m1_to_label = self._label("To")
        _m1_step_label = self._label("Step")
        self._m1_position_label = self._label("Position")
        _m1_label = self._label("Motor 1")
        _m1_label.setStyleSheet("qproperty-alignment: AlignRight;")

        self._m2_from_label = self._label("From")
        _m2_to_label = self._label("To")
        _m2_step_label = self._label("Step")
        self._m2_position_label = self._label("Position")
        _m2_label = self._label("Motor 2")
        _m2_label.setStyleSheet("qproperty-alignment: AlignRight;")

        _m3_from_label = self._label("From")
        _m3_to_label = self._label("To")
        _m3_step_label = self._label("Step")
        self._m3_position_label = self._label("Position")
        _m3_label = self._label("Motor 3")
        _m3_label.setStyleSheet("qproperty-alignment: AlignRight;")

        _calibration_title_label = self._label("Calibration:")
        _calibration_m1_label = self._label("Motor 1")
        _calibration_m2_label = self._label("Motor 2")
        _calibration_m3_label = self._label("Motor 3")
        _calibration_where_label = self._label("Where")
        _calibration_m3_range_label = self._label("Range")

        _measurement_setup_title_label = self._label("Measurement:")

        _measurement_num_label = self._label("Measurement points")
        _measurement_n_label = self._label("[n]")
        _scan_type_label = self._label("Scan type:")

        _home_title_label = self._label("Homing:")

        _time_to_finish_title_label = self._label("Time to Finish:")
        self._time_to_finish_value_label = self._label("0d 0h 0m 0s")

        _url_label = self._label(
            f"<a href='https://www.numsolution.cz/'>https://www.numsolution.cz/</a>"
        )
        _url_label.setOpenExternalLinks(True)

        # Line edits
        double_validator = QDoubleValidator()  # Line edit will accept only Double types.
        self._m1_from_value = self._line_edit(f"{controller.motor_1.scan_from}")
        self._m1_from_value.setValidator(double_validator)
        self._m1_from_value.editingFinished.connect(
            lambda: self._collect_data_from_line_edit(self._m1_from_value, 1, 'scan_from'))

        self._m1_to_value = self._line_edit(f"{controller.motor_1.scan_to}")
        self._m1_to_value.setValidator(double_validator)
        self._m1_to_value.editingFinished.connect(
            lambda: self._collect_data_from_line_edit(self._m1_to_value, 1, 'scan_to'))

        self._m1_step_value = self._line_edit(f"{controller.motor_1.scan_step}")
        self._m1_step_value.setValidator(double_validator)
        self._m1_step_value.editingFinished.connect(
            lambda: self._collect_data_from_line_edit(self._m1_step_value, 1, 'scan_step'))

        self._m1_move_to_value = self._line_edit("0")
        self._m1_move_to_value.setValidator(double_validator)

        self._m2_from_value = self._line_edit(f"{controller.motor_2.scan_from}")
        self._m2_from_value.setValidator(double_validator)
        self._m2_from_value.editingFinished.connect(
            lambda: self._collect_data_from_line_edit(self._m2_from_value, 2, 'scan_from'))

        self._m2_to_value = self._line_edit(f"{controller.motor_2.scan_to}")
        self._m2_to_value.setValidator(double_validator)
        self._m2_to_value.editingFinished.connect(
            lambda: self._collect_data_from_line_edit(self._m2_to_value, 2, 'scan_to'))

        self._m2_step_value = self._line_edit(f"{controller.motor_2.scan_step}")
        self._m2_step_value.setValidator(double_validator)
        self._m2_step_value.editingFinished.connect(
            lambda: self._collect_data_from_line_edit(self._m2_step_value, 2, 'scan_step'))

        self._m2_move_to_value = self._line_edit("0")
        self._m2_move_to_value.setValidator(double_validator)

        self._m3_from_value = self._line_edit(f"{controller.motor_3.scan_from}")
        self._m3_from_value.setValidator(double_validator)
        self._m3_from_value.editingFinished.connect(
            lambda: self._collect_data_from_line_edit(self._m3_from_value, 3, 'scan_from'))

        self._m3_to_value = self._line_edit(f"{controller.motor_3.scan_to}")
        self._m3_to_value.setValidator(double_validator)
        self._m3_to_value.editingFinished.connect(
            lambda: self._collect_data_from_line_edit(self._m3_to_value, 3, 'scan_to'))

        self._m3_step_value = self._line_edit(f"{controller.motor_3.scan_step}")
        self._m3_step_value.setValidator(double_validator)
        self._m3_step_value.editingFinished.connect(
            lambda: self._collect_data_from_line_edit(self._m3_step_value, 3, 'scan_step'))

        self._m3_move_to_value = self._line_edit("0")
        self._m3_move_to_value.setValidator(double_validator)

        self._calibration_m1_value = self._line_edit("80")
        self._calibration_m2_value = self._line_edit("90")
        self._calibration_m3_value = self._line_edit("80")
        self._calibration_m3_range_value = self._line_edit("10")

        int_validator = QIntValidator()
        self._number_of_measurement_points_value = self._line_edit("500")
        self._number_of_measurement_points_value.setValidator(int_validator)
        self._number_of_measurement_points_value.editingFinished.connect(
            lambda: controller.sensor.set_number_of_measurement_points(self._number_of_measurement_points_value.text()))

        # Buttons
        self._home1_button = self._push_button("Motor 1 Home")
        self._home1_button.clicked.connect(lambda: self.start_homing(1))
        self._home2_button = self._push_button("Motor 2 Home")
        self._home2_button.clicked.connect(lambda: self.start_homing(2))
        self._home3_button = self._push_button("Motor 3 Home")
        self._home3_button.clicked.connect(lambda: self.start_homing(3))
        self._home_all_button = self._push_button("Motor All")
        self._home_all_button.clicked.connect(lambda: self.start_homing_all())
        self._move_1_to_button = self._push_button("Move")
        self._move_1_to_button.clicked.connect(lambda: self.move_to(1, float(self._m1_move_to_value.text())))
        self._move_2_to_button = self._push_button("Move")
        self._move_2_to_button.clicked.connect(lambda: self.move_to(2, float(self._m2_move_to_value.text())))
        self._move_3_to_button = self._push_button("Move")
        self._move_3_to_button.clicked.connect(lambda: self.move_to(3, float(self._m3_move_to_value.text())))
        self._calibrate_button = self._push_button("Calibrate")
        self._calibrate_button.clicked.connect(
            lambda: self.start_calibration([self._calibration_m1_value.text(),
                                            self._calibration_m2_value.text(),
                                            self._calibration_m3_value.text(),
                                            self._calibration_m3_range_value.text(),
                                            self._m3_step_value.text(),
                                            self._number_of_measurement_points_value.text()
                                            ]))
        self._scan_button = self._push_button("Scan")
        self._scan_button.clicked.connect(lambda: self.start_scanning())
        self._graph_button = self._push_button("Graph")
        self._stop_button = self._push_button("STOP")
        self._stop_button.setFixedSize(80, 80)
        self._stop_button.setStyleSheet("QPushButton {background-color: rgb(255, 26, 26); color: white;}")
        self._stop_button.clicked.connect(lambda: self.stop_motors())
        self._connection_button = self._push_button("Disconnect")
        self._connection_button.clicked.connect(lambda: self.connect_or_disconnect_devices())

        self._graph_button.clicked.connect(lambda: self.toggle_scattering_graph_visibility())

        # Progress bar
        self._progress_bar = self._progress_bar(0)

        # Checkbox
        self._measurement_1d = QCheckBox("1D", self)
        self._measurement_3d = QCheckBox("3D", self)
        self._measurement_1d.setChecked(False)
        self._measurement_3d.setChecked(True)
        self._measurement_3d.setEnabled(False)
        self._measurement_1d.clicked.connect(self._restrict_value_editing_for_1d_scan)
        self._measurement_1d.clicked.connect(lambda: controller.set_scan_type('1D'))
        self._measurement_3d.clicked.connect(self._restrict_value_editing_for_3d_scan)
        self._measurement_3d.clicked.connect(lambda: controller.set_scan_type('3D'))

        # Logo
        # logo = self._create_logo()  # Currently unused

        # Place and display created widgets
        self._layout.addWidget(self._connection_button, 0, 2, 1, 1)
        self._layout.addWidget(_url_label, 0, 6, 1, 3)
        self._layout.addWidget(_controller_setup_title_label, 0, 0, 1, 2)
        self._layout.addWidget(QHLine(), 1, 0, 1, self._layout.columnCount())
        self._layout.addWidget(_motor_setup_title_label, 2, 0, 1, 1)
        self._layout.addWidget(self._m1_from_label, 3, 2, 1, 1)
        self._layout.addWidget(_m1_to_label, 3, 3, 1, 1)
        self._layout.addWidget(_m1_step_label, 3, 4, 1, 1)
        self._layout.addWidget(self._m1_position_label, 3, 6, 1, 1)
        self._layout.addWidget(_m1_label, 4, 1, 1, 1)
        self._layout.addWidget(self._m1_from_value, 4, 2, 1, 1)
        self._layout.addWidget(self._m1_to_value, 4, 3, 1, 1)
        self._layout.addWidget(self._m1_step_value, 4, 4, 1, 1)
        self._layout.addWidget(QVLine(), 4, 5, 1, 1)
        self._layout.addWidget(self._m1_move_to_value, 4, 6, 1, 1)
        self._layout.addWidget(self._move_1_to_button, 4, 7, 1, 1)
        self._layout.addWidget(self._m2_from_label, 5, 2, 1, 1)
        self._layout.addWidget(_m2_to_label, 5, 3, 1, 1)
        self._layout.addWidget(_m2_step_label, 5, 4, 1, 1)
        self._layout.addWidget(self._m2_position_label, 5, 6, 1, 1)
        self._layout.addWidget(_m2_label, 6, 1, 1, 1)
        self._layout.addWidget(self._m2_from_value, 6, 2, 1, 1)
        self._layout.addWidget(self._m2_to_value, 6, 3, 1, 1)
        self._layout.addWidget(self._m2_step_value, 6, 4, 1, 1)
        self._layout.addWidget(QVLine(), 6, 5, 1, 1)
        self._layout.addWidget(self._m2_move_to_value, 6, 6, 1, 1)
        self._layout.addWidget(self._move_2_to_button, 6, 7, 1, 1)
        self._layout.addWidget(_m3_from_label, 7, 2, 1, 1)
        self._layout.addWidget(_m3_to_label, 7, 3, 1, 1)
        self._layout.addWidget(_m3_step_label, 7, 4, 1, 1)
        self._layout.addWidget(self._m3_position_label, 7, 6, 1, 1)
        self._layout.addWidget(_m3_label, 8, 1, 1, 1)
        self._layout.addWidget(self._m3_from_value, 8, 2, 1, 1)
        self._layout.addWidget(self._m3_to_value, 8, 3, 1, 1)
        self._layout.addWidget(self._m3_step_value, 8, 4, 1, 1)
        self._layout.addWidget(QVLine(), 8, 5, 1, 1)
        self._layout.addWidget(self._m3_move_to_value, 8, 6, 1, 1)
        self._layout.addWidget(self._move_3_to_button, 8, 7, 1, 1)
        self._layout.addWidget(QHLine(), 9, 0, 1, self._layout.columnCount())
        self._layout.addWidget(_calibration_title_label, 10, 0, 1, 1)
        self._layout.addWidget(_calibration_m1_label, 11, 2, 1, 1)
        self._layout.addWidget(_calibration_m2_label, 11, 3, 1, 1)
        self._layout.addWidget(_calibration_m3_label, 11, 4, 1, 1)
        self._layout.addWidget(QVLine(), 12, 5, 1, 1)
        self._layout.addWidget(_calibration_m3_range_label, 11, 6, 1, 1)
        self._layout.addWidget(_calibration_where_label, 12, 1, 1, 1)
        self._layout.addWidget(self._calibration_m1_value, 12, 2, 1, 1)
        self._layout.addWidget(self._calibration_m2_value, 12, 3, 1, 1)
        self._layout.addWidget(self._calibration_m3_value, 12, 4, 1, 1)
        self._layout.addWidget(self._calibration_m3_range_value, 12, 6, 1, 1)
        self._layout.addWidget(self._calibrate_button, 12, 7, 1, 1)
        self._layout.addWidget(QHLine(), 14, 0, 1, self._layout.columnCount())
        self._layout.addWidget(_measurement_setup_title_label, 15, 0, 1, 1)
        self._layout.addWidget(_measurement_num_label, 16, 2, 1, 1)
        self._layout.addWidget(self._number_of_measurement_points_value, 16, 3, 1, 1)
        self._layout.addWidget(_measurement_n_label, 16, 4, 1, 1)
        self._layout.addWidget(_scan_type_label, 17, 2, 1, 1)
        self._layout.addWidget(self._measurement_1d, 17, 3, 1, 1)
        self._layout.addWidget(self._measurement_3d, 17, 4, 1, 1)
        self._layout.addWidget(self._scan_button, 18, 2, 1, 3)
        self._layout.addWidget(self._graph_button, 18, 6, 1, 2)
        self._layout.addWidget(_time_to_finish_title_label, 19, 2, 1, 1)
        self._layout.addWidget(self._time_to_finish_value_label, 19, 3, 1, 1)
        self._layout.addWidget(self._progress_bar, 20, 2, 1, 3)
        self._layout.addWidget(QHLine(), 21, 0, 1, self._layout.columnCount())
        self._layout.addWidget(_home_title_label, 22, 0, 1, 1)
        self._layout.addWidget(self._stop_button, 22, 6, 4, 3, alignment=Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._home1_button, 23, 2, 1, 1)
        self._layout.addWidget(self._home2_button, 23, 3, 1, 1)
        self._layout.addWidget(self._home3_button, 23, 4, 1, 1)
        self._layout.addWidget(self._home_all_button, 24, 3, 1, 1)

        # Perform these tasks at the start of the program
        self.start_background_tasks()
        # Disable movement until initial homing is done
        self._disable_every_widget(QPushButton)
        self._home_all_button.setEnabled(True)

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

    def update_motor_positions(self):
        self._m1_position_label.setText(f"Position: {round(controller.motor_1.current_position, 3)}")
        self._m2_position_label.setText(f"Position: {round(controller.motor_2.current_position, 3)}")
        self._m3_position_label.setText(f"Position: {round(controller.motor_3.current_position, 3)}")

    def _set_disconnected_layout(self):
        self._disable_every_widget(QPushButton)
        self._stop_button.setEnabled(True)
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
        self._m1_from_label.setText("Where")
        self._m2_from_label.setText("Where")
        self._m3_from_value.setText('270')
        self._m3_to_value.setText('90')

    def _restrict_value_editing_for_3d_scan(self):
        # First enable everything
        self._enable_every_widget(QLineEdit)
        # Disable what is needed
        self._measurement_3d.setEnabled(False)
        self._measurement_1d.setEnabled(True)
        self._measurement_1d.setChecked(False)

        self._m1_from_label.setText("From")
        self._m2_from_label.setText("From")
        self._m3_from_value.setText('0')
        self._m3_to_value.setText('90')

    def _reset_layout(self):
        self._progress_bar.setValue(0)

        self._enable_every_widget()

        self._measurement_1d.setChecked(False)
        self._measurement_3d.setChecked(True)
        self._measurement_3d.setEnabled(False)
        self._m1_from_label.setText("From")
        self._m2_from_label.setText("From")

    def _update_progress_bar_label(self, finish_time):
        delta = timedelta(seconds=finish_time)
        (days, hours, minutes, seconds) = days_hours_minutes_seconds(delta)
        n = (str(days) + "d " + str(hours) + "h " + str(minutes) + "m " + str(seconds) + "s")
        self._time_to_finish_value_label.setText(n)

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
        if self.graph_2d.isVisible():
            self.graph_2d.hide()

        else:
            self.graph_2d.show()
            self.graph_2d.reset_max_value()
            plt.show()

    @staticmethod
    def _collect_data_from_line_edit(edited_line: QLineEdit, motor_id, parameter):
        # This function is a bit wild, but it does what it is supposed to do while keeping the rest of the code simple.
        value = float(edited_line.text())
        affected_motor = controller.__getattribute__(f'motor_{motor_id}')
        scan_from = value if parameter == 'scan_from' else None
        scan_to = value if parameter == 'scan_to' else None
        scan_step = value if parameter == 'scan_step' else None
        edited_line.editingFinished.connect(affected_motor.set_measurement_parameters(
            scan_from=scan_from, scan_to=scan_to, scan_step=scan_step))
        edited_line.setText(str(affected_motor.__getattribute__(f'{parameter}')))

    #  -----------------------------------------------------------------------------------    Hardware control functions
    def start_background_tasks(self):
        worker = BackgroundTasksThread(self)
        self.workers.append(worker)  # Associating the worker with the object prevents crashing

        worker.start()

    def start_calibration(self, input_data):
        worker = CalibratingThread(input_data)
        self.workers.append(worker)
        # self.sensor_real_time_graph.timer.stop()
        worker.start()
        worker.finished.connect(lambda: self.graph_2d.timer.start())

    def start_homing(self, motor_id):
        worker = HomingThread(motor_id)
        self.workers.append(worker)
        self.__getattribute__(f'_home{motor_id}').setEnabled(False)  # Disable homing button for current motor
        self._home_all_button.setEnabled(False)
        worker.start()
        # Enable homing button for the current motor once homing finished
        worker.finished.connect(lambda: self.__getattribute__(f'_home{motor_id}').setEnabled(True))
        worker.finished.connect(lambda: self._home_all_button.setEnabled(True))

    def start_homing_all(self):
        self.start_homing(1)
        self.start_homing(2)
        self.start_homing(3)
        self._enable_every_widget(QPushButton)

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
        # TODO: Clear unnecessary input data
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
        worker.thread_signal.connect(self._update_progress_bar)

        self._disable_every_widget(QPushButton)
        self._stop_button.setEnabled(True)
        self._graph_button.setEnabled(True)

        worker.start()

        worker.finished.connect(self._reset_layout)

    def stop_motors(self):
        controller.stop_motors_and_disconnect()
        self._set_disconnected_layout()

    def connect_or_disconnect_devices(self):
        if self._connection_button.text() == "Connect":
            _connection_check = controller.connect()  # Connects to the controller and returns 0 if connected correctly
            if _connection_check == 1:
                self._set_disconnected_layout()
                # Not connected (Error)
                return 1
            elif _connection_check == 0:
                # Connected
                self._set_connected_layout()
        elif self._connection_button.text() == "Disconnect":
            controller.disconnect()
            self._set_disconnected_layout()


class CalibratingThread(QThread):
    def __init__(self, input_data):
        super().__init__()
        self.input_data = input_data

    def run(self) -> None:
        controller.calibrate(self.input_data)
        return


# Threads for moving the motors:
class HomingThread(QThread):

    def __init__(self, motor_id: int):
        super().__init__()
        self._active_motor = controller.motors[motor_id]

    def run(self) -> None:
        self._active_motor.home()
        return


class MovingThread(QThread):

    def __init__(self, motor_id, position):
        super().__init__()
        self._position = position
        self._active_motor = controller.motors[motor_id]

    def run(self) -> None:
        self._active_motor.move_to_position(self._position)
        return


class ScanningThread(QThread):
    thread_signal = Signal(list)

    def __init__(self, input_data):
        super().__init__()
        self.input_data = input_data

    def run(self) -> None:
        controller.scanning(self.thread_signal)
        return


class BackgroundTasksThread(QThread):
    def __init__(self, active_window: Window):
        super().__init__()
        self.active_window = active_window

    def run(self) -> None:
        while self.active_window.isWindow():
            self.active_window.update_motor_positions()
            time.sleep(0.5)  # To not overload the program check for position only twice per second.
        return


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
