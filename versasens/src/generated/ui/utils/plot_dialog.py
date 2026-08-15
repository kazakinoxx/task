# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'plot_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_PlotDialog(object):
    def setupUi(self, PlotDialog):
        if not PlotDialog.objectName():
            PlotDialog.setObjectName(u"PlotDialog")
        PlotDialog.resize(1000, 700)
        self.base_layout = QVBoxLayout(PlotDialog)
        self.base_layout.setObjectName(u"base_layout")
        self.top_layout = QHBoxLayout()
        self.top_layout.setObjectName(u"top_layout")
        self.label = QLabel(PlotDialog)
        self.label.setObjectName(u"label")

        self.top_layout.addWidget(self.label)


        self.base_layout.addLayout(self.top_layout)

        self.placeholder = QWidget(PlotDialog)
        self.placeholder.setObjectName(u"placeholder")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.placeholder.sizePolicy().hasHeightForWidth())
        self.placeholder.setSizePolicy(sizePolicy)

        self.base_layout.addWidget(self.placeholder)


        self.retranslateUi(PlotDialog)

        QMetaObject.connectSlotsByName(PlotDialog)
    # setupUi

    def retranslateUi(self, PlotDialog):
        PlotDialog.setWindowTitle(QCoreApplication.translate("PlotDialog", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("PlotDialog", u"Right click on any graph to show options.", None))
    # retranslateUi

