import sys

from PySide6.QtWidgets import QApplication

import _gui

# TODO: motor 3 from 90 60 30 0 270 300 330 does not graph properly  (Software)
# FIXME: Motor 3 2 1 positions display in GUI is stuck
# TODO: TEST periodical data measurement for real time graph  (Hardware)
# FIXME: Doesnt graph motor 1 at 60 degrees  (Hardware)


def main():
    # Create the Qt Application
    app = QApplication([])
    window = _gui.Window()
    window.show()
    window_termination = app.exec()
    _gui.controller.disconnect()
    sys.exit(window_termination)


if __name__ == '__main__':
    main()
