import math

from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout
from PySide6.QtCore import QTimer, QSize
import pyqtgraph as pg
import numpy as np
from matplotlib import colormaps
import matplotlib.animation

matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

# Custom libraries
from modules import backend

controller = backend.motor_controller


class Graph2D:
    def __init__(self):
        self.graphWidget = pg.PlotWidget()
        self.time = [0.0]
        self.a0_values = [0.0]
        self.a0_max_values = [0.0]
        self.time_window = 50  # [s]
        self.time_interval = 50  # [ms]

        self.graphWidget.setBackground('w')
        self.graphWidget.showGrid(x=True, y=True)
        pen = pg.mkPen(color=(255, 0, 0))
        pen_blue = pg.mkPen(color=(0, 0, 255))
        self.data_line = self.graphWidget.plot(self.time, self.a0_values, pen=pen)
        self.data_line_2 = self.graphWidget.plot(self.time, self.a0_max_values, pen=pen_blue)
        self.max_a0_text = pg.TextItem(f"Max A0 = {self.a0_max_values}", anchor=(1, 0), color=(0, 0, 255))
        self.graphWidget.addItem(self.max_a0_text)
        self.timer = QTimer()
        self.timer.setInterval(self.time_interval)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.timeout.connect(controller.sensor.measure_scattering)
        self.timer.start()

    def update_plot_data(self):
        # Remove the first values in the list to clear memory
        if len(self.time) > self.time_window:
            self.time = self.time[1:]
            self.a0_values = self.a0_values[1:]
            self.a0_max_values = self.a0_max_values[1:]

        self.time.append(self.time[-1] + self.time_interval / 100)  # Update time by the time interval
        self.a0_values.append(controller.sensor.get_last_measurement()[0])
        self.a0_max_values.append(controller.sensor.max_value_a0)
        self.data_line.setData(self.time, self.a0_values)  # Update the data.
        self.data_line_2.setData(self.time, self.a0_max_values)  # Update the data.
        self.max_a0_text.setText(f"Max A0 = {round(self.a0_max_values[-1], 7)}")
        self.max_a0_text.setPos(self.time[-1], self.a0_max_values[-1])

    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start()

    def reset_max_value(self):
        controller.sensor.max_value_a0 = self.a0_values[-1]


class _MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=10, height=7, dpi=100):
        self.parent = parent
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111, projection='3d')
        super().__init__(fig)


class Graph3D:
    def __init__(self):
        # Create the Matplotlib canvas and get its axes
        self.canvas = _MplCanvas(self)
        self.axes = self.canvas.axes

        self.plot_data = controller.measurement_data
        self.measurement_colormaps = None

        np.random.seed(19680801)

        self.axes.view_init(0, 90)

        # Axis labels
        self.axes.set_xlabel('Motor 3 angle')
        self.axes.set_ylabel('Motor 2 angle')
        self.axes.set_zlabel('A0')

        # Set continuous ticks and wrapping formatter
        self.axes.set_xticks(controller.motor_3.scan_positions)
        self.axes.xaxis.set_major_formatter(FuncFormatter(self.wrap_angle))
        self.axes.set_yticks(controller.motor_2.scan_positions)

        # Animation
        self.ani = matplotlib.animation.FuncAnimation(
            self.canvas.figure, self.update, frames=100
        )

    @staticmethod
    def wrap_angle(angle, pos):
        return int(angle % 360)

    def update(self, t):
        _ = t
        self.clear_graph()
        self.prepare_color_scheme()

        for i, motor_1_position in enumerate(controller.motor_1.scan_positions):
            for j, motor_2_position in enumerate(controller.motor_2.scan_positions):
                x = []
                y = []
                color_scale_factor = 1 - (i / len(controller.motor_1.scan_positions))

                for data_entry in self.plot_data:
                    if data_entry['motor_3_position'] < 270:
                        data_entry['motor_3_position'] += 360
                    if (math.isclose(data_entry['motor_1_position'], motor_1_position, abs_tol=0.5) and
                            math.isclose(data_entry['motor_2_position'], motor_2_position, abs_tol=0.5)):
                        x.append(data_entry['motor_3_position'])  # continuous angle
                        y.append(data_entry['a0'])

                self.axes.plot(
                    x, y, zs=motor_2_position, zdir='y',
                    color=self.measurement_colormaps[j](color_scale_factor),
                    alpha=0.8
                )

        return []

    def prepare_color_scheme(self):
        sequential_colormaps = [
            'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
            'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu', 'GnBu',
            'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn'
        ]

        for i, color in enumerate(sequential_colormaps):
            sequential_colormaps[i] = colormaps[color].resampled(
                len(controller.motor_1.scan_positions)
            )

        sequential_colormaps = sequential_colormaps[:len(controller.motor_2.scan_positions)]
        self.measurement_colormaps = sequential_colormaps

    def clear_graph(self):
        raw_positions = controller.motor_3.scan_positions
        for i, position in enumerate(raw_positions):
            if position < 270:
                raw_positions[i] += 360
        self.axes.set_xticks(raw_positions)
        self.axes.set_xlim([raw_positions[0] - 10, raw_positions[-1] + 10])
        self.axes.xaxis.set_major_formatter(FuncFormatter(self.wrap_angle))

        self.axes.set_yticks(controller.motor_2.scan_positions)
        self.axes.set_ylim([
            controller.motor_2.scan_positions[0] - 10,
            controller.motor_2.scan_positions[-1] + 10
        ])

        for art in list(self.axes.lines):
            art.remove()

        self.ani.resume()


class GraphWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Window setup
        _central_widget = QWidget()
        self.setCentralWidget(_central_widget)
        self._layout = QGridLayout()
        _central_widget.setLayout(self._layout)

        self.setWindowTitle("Graphs")
        self.setFixedSize(QSize(640, 600))

        self.graph_2d = Graph2D()
        self.graph_3d = Graph3D()
        self.toolbar = NavigationToolbar(self.graph_3d.canvas, self)
        self._layout.addWidget(self.toolbar)
        self._layout.addWidget(self.graph_2d.graphWidget, 2, 0)
        self._layout.addWidget(self.graph_3d.canvas, 1, 0)
