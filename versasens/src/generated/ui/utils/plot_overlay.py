# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'plot_overlay.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QLabel, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_PauseOverlay(object):
    def setupUi(self, PauseOverlay):
        if not PauseOverlay.objectName():
            PauseOverlay.setObjectName(u"PauseOverlay")
        PauseOverlay.resize(453, 301)
        PauseOverlay.setAutoFillBackground(False)
        PauseOverlay.setStyleSheet(u"background-color: rgba(0, 0, 0, 150);")
        self.verticalLayout = QVBoxLayout(PauseOverlay)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(PauseOverlay)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(32)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout.addWidget(self.label)


        self.retranslateUi(PauseOverlay)

        QMetaObject.connectSlotsByName(PauseOverlay)
    # setupUi

    def retranslateUi(self, PauseOverlay):
        PauseOverlay.setWindowTitle(QCoreApplication.translate("PauseOverlay", u"Form", None))
        self.label.setText(QCoreApplication.translate("PauseOverlay", u"PAUSED", None))
    # retranslateUi

