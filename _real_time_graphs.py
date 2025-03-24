import random

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer
import pyqtgraph as pg
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colormaps
import matplotlib.animation

# Custom libraries
import _backend

controller = _backend.BSC203ThreeChannelBenchtopStepperMotorController


class Graph2D(QMainWindow):
    def __init__(self):
        super().__init__()
        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)

        self.time = [0.0]
        self.ad0_values = [0.0]
        self.ad0_max_values = [0.0]
        self.time_window = 50  # [s]
        self.time_interval = 50  # [ms]

        self.graphWidget.setBackground('w')
        self.graphWidget.showGrid(x=True, y=True)
        pen = pg.mkPen(color=(255, 0, 0))
        pen_blue = pg.mkPen(color=(0, 0, 255))
        self.data_line = self.graphWidget.plot(self.time, self.ad0_values, pen=pen)
        self.data_line_2 = self.graphWidget.plot(self.time, self.ad0_max_values, pen=pen_blue)
        self.max_ad0_text = pg.TextItem(f"Max AD0 = {self.ad0_max_values}", anchor=(1, 1), color=(0, 0, 255))
        self.max_ad0_text.setPos(1, 1)
        self.graphWidget.addItem(self.max_ad0_text)
        self.timer = QTimer()
        self.timer.setInterval(self.time_interval)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.timeout.connect(self.try_to_measure_scattering)
        self.timer.start()

    def update_plot_data(self):
        # Remove the first values in the list to clear memory
        if len(self.time) > self.time_window:
            self.time = self.time[1:]
            self.ad0_values = self.ad0_values[1:]
            self.ad0_max_values = self.ad0_max_values[1:]

        self.time.append(self.time[-1] + self.time_interval/100)  # Update time by the time interval
        self.ad0_values.append(controller.sensor.get_last_measurement()[0])
        self.ad0_max_values.append(controller.sensor.max_value_ad_0)
        self.data_line.setData(self.time, self.ad0_values)  # Update the data.
        self.data_line_2.setData(self.time, self.ad0_max_values)  # Update the data.
        self.max_ad0_text.setText(f"Max AD0 = {self.ad0_max_values[-1]}")
        self.max_ad0_text.setPos(self.time[-1], self.ad0_max_values[-1])

    @staticmethod
    def try_to_measure_scattering():
        try:
            controller.sensor.measure_scattering()
        except:
            # TODO: Specify exception
            pass

    def reset_max_value(self):
        controller.sensor.max_value_ad_0 = self.ad0_values[-1]


class Graph3D:
    def __init__(self):
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(projection='3d')
        self.plot_data = controller.measured_data

        motor_2_scan_positions = controller.motor_2.scan_positions
        motor_3_scan_positions = controller.motor_3.scan_positions

        np.random.seed(19680801)

        self.ax.view_init(0, 90)

        self.ax.set_xlabel('Motor 3 angle')
        self.ax.set_xticks(motor_3_scan_positions)
        self.ax.set_ylabel('Motor 2 angle')
        self.ax.set_yticks(motor_2_scan_positions)
        self.ax.set_zlabel('A0')

        self.ani = matplotlib.animation.FuncAnimation(self.fig, self.update, frames=100)

        self.lines = []
        for position in controller.motor_2.scan_positions:
            x = controller.motor_3.scan_positions
            y = np.random.randint(69, size=len(x))
            self.lines.append(self.ax.plot(x, y, zs=position, zdir='y', alpha=0.8))

    def update(self, t):
        _ = t  # t is not used. delete it.
        self.ax.set_xticks(controller.motor_3.scan_positions)
        self.ax.set_yticks(controller.motor_2.scan_positions)
        plasma = colormaps['plasma'].resampled(100)
        # Clear previous lines in graph
        for art in list(self.ax.lines):
            art.remove()

        for motor_1_position in controller.motor_1.scan_positions:
            for motor_2_position in controller.motor_2.scan_positions:
                x = []
                y = []
                for data_entry in self.plot_data:
                    if data_entry[0][0] == motor_1_position and data_entry[0][1] == motor_2_position:
                        x.append(data_entry[0][2])
                        y.append(data_entry[1][0])
                self.ax.plot(x, y, zs=motor_2_position, zdir='y',
                             color=plasma(motor_2_position / 100 + motor_1_position/500), alpha=0.8)

        return []  # Return [] to prevent pycharm warnings but no other reason.


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Graph2D()
    main.show()
    app.exec()
