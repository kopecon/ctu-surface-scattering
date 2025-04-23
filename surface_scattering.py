import sys

from PySide6.QtWidgets import QApplication

import _gui


# FIXME: Scan type does not reset along with the GUI
# TODO: motor 3 from 90 60 30 0 270 300 330 does not graph properly
# FIXME: Motor 3 2 1 positions display in GUI is stuck
# TODO: Solve periodical data measurement for real time graph
# FIXME: Doesnt graph motor 1 at 60 degrees
# FIXME: Home button clears graphs
# TODO: Switch from rounding to is close
if __name__ == '__main__':
    # Create the Qt Application
    app = QApplication([])
    window = _gui.Window()
    window.show()
    window_termination = app.exec()
    _gui.controller.disconnect()
    sys.exit(window_termination)
