from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer
import pyqtgraph as pg
import sys

# Custom libraries
from _sensor import measure_scattering


class GraphWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)

        self.x = [0.0]
        self.y = [0.0]

        self.graphWidget.setBackground('w')

        pen = pg.mkPen(color=(255, 0, 0))
        self.data_line = self.graphWidget.plot(self.x, self.y, pen=pen)

        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def update_plot_data(self):
        if len(self.x) > 50:
            self.x = self.x[1:]  # Remove the first
            self.y = self.y[1:]  # Remove the first

        self.x.append(self.x[-1] + 0.5)  # Add a new value 1 higher than the last.
        self.y.append(measure_scattering()[0])
        self.data_line.setData(self.x, self.y)  # Update the data.


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = GraphWindow()
    main.show()
    app.exec()
