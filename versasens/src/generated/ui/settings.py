# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settings.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QDoubleSpinBox, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_Settings(object):
    def setupUi(self, Settings):
        if not Settings.objectName():
            Settings.setObjectName(u"Settings")
        Settings.resize(433, 197)
        self.verticalLayout = QVBoxLayout(Settings)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(Settings)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.open_button = QPushButton(Settings)
        self.open_button.setObjectName(u"open_button")

        self.horizontalLayout.addWidget(self.open_button)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.line = QFrame(Settings)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_2 = QLabel(Settings)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(120, 0))
        self.label_2.setMaximumSize(QSize(120, 16777215))

        self.horizontalLayout_2.addWidget(self.label_2)

        self.db_lineedit = QLineEdit(Settings)
        self.db_lineedit.setObjectName(u"db_lineedit")
        self.db_lineedit.setEnabled(False)

        self.horizontalLayout_2.addWidget(self.db_lineedit)

        self.db_button = QPushButton(Settings)
        self.db_button.setObjectName(u"db_button")
        self.db_button.setMaximumSize(QSize(30, 16777215))

        self.horizontalLayout_2.addWidget(self.db_button)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.plot_x_axis_length_layout = QHBoxLayout()
        self.plot_x_axis_length_layout.setObjectName(u"plot_x_axis_length_layout")
        self.plot_x_axis_length_label = QLabel(Settings)
        self.plot_x_axis_length_label.setObjectName(u"plot_x_axis_length_label")

        self.plot_x_axis_length_layout.addWidget(self.plot_x_axis_length_label)

        self.x_axis_length = QDoubleSpinBox(Settings)
        self.x_axis_length.setObjectName(u"x_axis_length")
        self.x_axis_length.setDecimals(4)

        self.plot_x_axis_length_layout.addWidget(self.x_axis_length)


        self.verticalLayout.addLayout(self.plot_x_axis_length_layout)

        self.ads_vref_layout = QHBoxLayout()
        self.ads_vref_layout.setObjectName(u"ads_vref_layout")
        self.ads_vref_label = QLabel(Settings)
        self.ads_vref_label.setObjectName(u"ads_vref_label")

        self.ads_vref_layout.addWidget(self.ads_vref_label)

        self.ads_vref = QSpinBox(Settings)
        self.ads_vref.setObjectName(u"ads_vref")

        self.ads_vref_layout.addWidget(self.ads_vref)


        self.verticalLayout.addLayout(self.ads_vref_layout)

        self.ads_gain_layout = QHBoxLayout()
        self.ads_gain_layout.setObjectName(u"ads_gain_layout")
        self.ads_gain_label = QLabel(Settings)
        self.ads_gain_label.setObjectName(u"ads_gain_label")

        self.ads_gain_layout.addWidget(self.ads_gain_label)

        self.ads_gain = QSpinBox(Settings)
        self.ads_gain.setObjectName(u"ads_gain")

        self.ads_gain_layout.addWidget(self.ads_gain)


        self.verticalLayout.addLayout(self.ads_gain_layout)


        self.retranslateUi(Settings)

        QMetaObject.connectSlotsByName(Settings)
    # setupUi

    def retranslateUi(self, Settings):
        Settings.setWindowTitle(QCoreApplication.translate("Settings", u"Settings", None))
        self.label.setText(QCoreApplication.translate("Settings", u"Config file", None))
        self.open_button.setText(QCoreApplication.translate("Settings", u"Open file", None))
        self.label_2.setText(QCoreApplication.translate("Settings", u"Database Path", None))
        self.db_button.setText(QCoreApplication.translate("Settings", u"...", None))
        self.plot_x_axis_length_label.setText(QCoreApplication.translate("Settings", u"Plot X Axis Length", None))
        self.x_axis_length.setSuffix(QCoreApplication.translate("Settings", u" seconds", None))
        self.ads_vref_label.setText(QCoreApplication.translate("Settings", u"ADS V_REF", None))
        self.ads_gain_label.setText(QCoreApplication.translate("Settings", u"ADS Gain", None))
    # retranslateUi

