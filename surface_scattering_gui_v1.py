from PySide6.QtGui import QPixmap
from PySide6.QtCore import QSize, Qt
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

# Custom packages from this project
from surface_scattering_backend_v1 import WorkerHome, WorkerMove


class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Thorlab 3 Wheel")
        self.setFixedSize(QSize(600, 600))

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        self.createLabels()
        self.createLineEdits()
        self.createButtons()
        self.createProgressBars()
        self.createLogo()
        self.createCheckboxs()

        self.layout = QGridLayout()
        centralWidget.setLayout(self.layout)
        self.layout.addWidget(self.labelMSETUPtitle, 0, 0, 1, 1)
        self.layout.addWidget(self.labelM1from, 1, 1, 1, 1)
        self.layout.addWidget(self.labelM1to, 1, 2, 1, 1)
        self.layout.addWidget(self.labelM1step, 1, 3, 1, 1)
        self.layout.addWidget(self.labelM1, 2, 0, 1, 1)
        self.layout.addWidget(self.labelM2from, 4, 1, 1, 1)
        self.layout.addWidget(self.labelM2to, 4, 2, 1, 1)
        self.layout.addWidget(self.labelM2step, 4, 3, 1, 1)
        self.layout.addWidget(self.labelM2, 5, 0, 1, 1)
        self.layout.addWidget(self.labelM3from, 6, 1, 1, 1)
        self.layout.addWidget(self.labelM3to, 6, 2, 1, 1)
        self.layout.addWidget(self.labelM3step, 6, 3, 1, 1)
        self.layout.addWidget(self.labelM3, 7, 0, 1, 1)
        self.layout.addWidget(self.labelMESSETUPtitle, 9, 0, 1, 1)
        self.layout.addWidget(self.labelMESnum, 10, 0, 1, 1)
        self.layout.addWidget(self.labelMESn, 10, 2, 1, 1)
        self.layout.addWidget(self.labelHOMEtitle, 12, 0, 1, 1)
        self.layout.addWidget(self.labelTIMEFtitle, 12, 3, 1, 1)
        self.layout.addWidget(self.labelTIMEFvalue, 12, 4, 1, 1)
        self.layout.addWidget(self.M1FROMvalue, 2, 1, 1, 1)
        self.layout.addWidget(self.M1TOvalue, 2, 2, 1, 1)
        self.layout.addWidget(self.M1STEPvalue, 2, 3, 1, 1)
        self.layout.addWidget(self.M2FROMvalue, 5, 1, 1, 1)
        self.layout.addWidget(self.M2TOvalue, 5, 2, 1, 1)
        self.layout.addWidget(self.M2STEPvalue, 5, 3, 1, 1)
        self.layout.addWidget(self.M3FROMvalue, 7, 1, 1, 1)
        self.layout.addWidget(self.M3TOvalue, 7, 2, 1, 1)
        self.layout.addWidget(self.M3STEPvalue, 7, 3, 1, 1)
        self.layout.addWidget(self.MESPOINTSvalue, 10, 1, 1, 1)
        self.layout.addWidget(self.STARTMESS, 11, 3, 1, 1)
        self.layout.addWidget(self.HOME1, 13, 1, 1, 1)
        self.layout.addWidget(self.HOME2, 14, 1, 1, 1)
        self.layout.addWidget(self.HOME3, 15, 1, 1, 1)
        self.layout.addWidget(self.Progress, 13, 3, 1, 2)
        self.layout.addWidget(self.urlLabel, 17, 4, 1, 1)
        self.layout.addWidget(self.mylogo, 0, 4, 1, 2)
        self.layout.addWidget(self.onedmeasurement, 11, 4, 1, 1)

    def createLabels(self):
        self.labelMSETUPtitle = self.createLabel("Motors Setup:")

        self.labelM1from = self.createLabel("From")
        self.labelM1to = self.createLabel("To")
        self.labelM1step = self.createLabel("Step")
        self.labelM1 = self.createLabel("Motor 1")

        self.labelM2from = self.createLabel("From")
        self.labelM2to = self.createLabel("To")
        self.labelM2step = self.createLabel("Step")
        self.labelM2 = self.createLabel("Motor 2")

        self.labelM3from = self.createLabel("From")
        self.labelM3to = self.createLabel("To")
        self.labelM3step = self.createLabel("Step")
        self.labelM3 = self.createLabel("Motor 3")

        self.labelMESSETUPtitle = self.createLabel("Measurement Setup:")

        self.labelMESnum = self.createLabel("N Measurement points")
        self.labelMESn = self.createLabel("[n]")

        self.labelHOMEtitle = self.createLabel("Homing:")

        self.labelTIMEFtitle = self.createLabel("Time to Finish:")
        self.labelTIMEFvalue = self.createLabel("0d 0h 0m 0s")

        self.urlLabel = self.createLabel(
            f"<a href='https://www.numsolution.cz/'>https://www.numsolution.cz/</a>"
        )
        self.urlLabel.setOpenExternalLinks(True)

    def createLabel(self, text: str) -> QLabel:
        label = QLabel()
        label.setText(text)
        return label

    def createLineEdits(self):
        self.M1FROMvalue = self.createLineEdit("0")
        self.M1TOvalue = self.createLineEdit("90")
        self.M1STEPvalue = self.createLineEdit("30")

        self.M2FROMvalue = self.createLineEdit("90")
        self.M2TOvalue = self.createLineEdit("180")
        self.M2STEPvalue = self.createLineEdit("30")

        self.M3FROMvalue = self.createLineEdit("0")
        self.M3TOvalue = self.createLineEdit("90")
        self.M3STEPvalue = self.createLineEdit("30")

        self.MESPOINTSvalue = self.createLineEdit("500")

    def createLineEdit(self, text: str) -> QLineEdit:
        lineEdit = QLineEdit()
        lineEdit.setText(text)
        return lineEdit

    def createButtons(self):
        self.STARTMESS = self.createButton("Start Measurement")
        self.HOME1 = self.createButton("Motor 1 Home")
        self.HOME2 = self.createButton("Motor 2 Home")
        self.HOME3 = self.createButton("Motor 3 Home")

        self.STARTMESS.clicked.connect(lambda: self.functionMove())

        self.HOME1.clicked.connect(
            lambda: self.functionHome(1, self.M1FROMvalue.text())
        )
        self.HOME2.clicked.connect(
            lambda: self.functionHome(2, self.M2FROMvalue.text())
        )
        self.HOME3.clicked.connect(
            lambda: self.functionHome(3, self.M3FROMvalue.text())
        )

    def createButton(self, text: str) -> QPushButton:
        pushButton = QPushButton()
        pushButton.setText(text)
        return pushButton

    def createProgressBars(self):
        self.Progress = self.createProgressBar(0)

    def createProgressBar(self, num: int) -> QProgressBar:
        progressBar = QProgressBar()
        progressBar.setValue(num)
        return progressBar

    def createLogo(self):
        self.LOGO = QPixmap("NUMlogo_200x93.png")
        self.LOGO = self.LOGO.scaledToWidth(100, Qt.SmoothTransformation)
        self.mylogo = QLabel()
        self.mylogo.setAlignment(Qt.AlignRight)
        self.mylogo.setPixmap(self.LOGO)

    def createCheckboxs(self):
        self.onedmeasurement = QCheckBox("1D Measurement", self)
        self.onedmeasurement.setChecked(False)
        self.onedmeasurement.clicked.connect(self.functionOneDmeasurement)

    def functionOneDmeasurement(self):
        if self.onedmeasurement.isChecked() == True:
            self.M1TOvalue.setEnabled(False)
            self.M1STEPvalue.setEnabled(False)
            self.M2TOvalue.setEnabled(False)
            self.M2STEPvalue.setEnabled(False)
            self.M3FROMvalue.setEnabled(False)
            self.M3TOvalue.setEnabled(False)

        else:
            self.M1TOvalue.setEnabled(True)
            self.M1STEPvalue.setEnabled(True)
            self.M2TOvalue.setEnabled(True)
            self.M2STEPvalue.setEnabled(True)
            self.M3FROMvalue.setEnabled(True)
            self.M3TOvalue.setEnabled(True)

    def functionMove(self):
        if self.onedmeasurement.isChecked() == True:
            self.oned = 1
            print("1D measurement ON")
        else:
            self.oned = 0
            print("1D measurement OFF")

        self.imputdata = [
            self.M1FROMvalue.text(),
            self.M1TOvalue.text(),
            self.M1STEPvalue.text(),
            self.M2FROMvalue.text(),
            self.M2TOvalue.text(),
            self.M2STEPvalue.text(),
            self.M3FROMvalue.text(),
            self.M3TOvalue.text(),
            self.M3STEPvalue.text(),
            self.MESPOINTSvalue.text(),
            self.oned,
        ]
        print("Data(functionMove): ", self.imputdata)
        self.myworkermove = WorkerMove(self.imputdata)
        self.myworkermove.finished.connect(
            self.finihedMove
        )  # propojeni signalu
        self.myworkermove.on_progress.connect(
            self.progressMove
        )  # propojeni signalu

        self.myworkermove.on_progress2.connect(
            self.progressMove2
        )  # propojeni signalu

        print("Run Move Function")

        self.STARTMESS.setEnabled(False)
        self.HOME1.setEnabled(False)
        self.HOME2.setEnabled(False)
        self.HOME3.setEnabled(False)

        self.myworkermove.start()

    def finihedMove(self):
        self.Progress.setValue(100)
        self.STARTMESS.setEnabled(True)
        self.HOME1.setEnabled(True)
        self.HOME2.setEnabled(True)
        self.HOME3.setEnabled(True)
        print("konec")

    def progressMove(self, n):
        self.Progress.setValue(n)
        print("Progress num:", n)

    def days_hours_minutes_seconds(self, dt):
        return (
            dt.days,  # days
            dt.seconds // 3600,  # hours
            (dt.seconds // 60) % 60,  # minutes
            dt.seconds
            - ((dt.seconds // 3600) * 3600)
            - ((dt.seconds % 3600 // 60) * 60),
            # seconds
        )

    def progressMove2(self, dm: float):
        delta = timedelta(seconds=dm)
        (days, hours, minutes, seconds) = self.days_hours_minutes_seconds(
            delta
        )
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
        self.labelTIMEFvalue.setText(n)

    def functionHome(self, motornum, M1Fromvalue):
        self.myworkerhome = WorkerHome(motornum)
        self.myworkerhome.finished.connect(
            self.finihedHome
        )  # propojeni signalu
        self.myworkerhome.on_progress.connect(
            self.progressHome
        )  # propojeni signalu

        print("Clicket motor:", motornum)
        print("self.MXFROMvalue:", M1Fromvalue)
        self.STARTMESS.setEnabled(False)
        self.HOME1.setEnabled(False)
        self.HOME2.setEnabled(False)
        self.HOME3.setEnabled(False)

        self.myworkerhome.start()

    def finihedHome(self):
        self.Progress.setValue(0)
        self.STARTMESS.setEnabled(True)
        self.HOME1.setEnabled(True)
        self.HOME2.setEnabled(True)
        self.HOME3.setEnabled(True)
        print("konec")

    def progressHome(self, n):
        self.Progress.setValue(n)
        print("Progress num:", n)


if __name__ == "__main__":
    # Create the Qt Applocation
    app = QApplication([])
    window = Window()
    window.show()
    sys.exit(app.exec())
