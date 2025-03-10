import sys

from PySide6.QtWidgets import QApplication

import _gui


if __name__ == '__main__':
    # Create the Qt Application
    app = QApplication([])
    window = _gui.Window()
    window.show()
    window_termination = app.exec()
    _gui.controller.disconnect()
    sys.exit(window_termination)
