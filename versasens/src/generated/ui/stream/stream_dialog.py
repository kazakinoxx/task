# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stream_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_StreamDialog(object):
    def setupUi(self, StreamDialog):
        if not StreamDialog.objectName():
            StreamDialog.setObjectName(u"StreamDialog")
        StreamDialog.resize(714, 450)
        self.verticalLayout = QVBoxLayout(StreamDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.header_layout = QWidget(StreamDialog)
        self.header_layout.setObjectName(u"header_layout")
        self.horizontalLayout = QHBoxLayout(self.header_layout)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, -1)
        self.view_stream_label = QLabel(self.header_layout)
        self.view_stream_label.setObjectName(u"view_stream_label")

        self.horizontalLayout.addWidget(self.view_stream_label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.device_box = QComboBox(self.header_layout)
        self.device_box.setObjectName(u"device_box")
        self.device_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        self.horizontalLayout.addWidget(self.device_box)

        self.refresh_button = QPushButton(self.header_layout)
        self.refresh_button.setObjectName(u"refresh_button")

        self.horizontalLayout.addWidget(self.refresh_button)


        self.verticalLayout.addWidget(self.header_layout)

        self.main_layout = QWidget(StreamDialog)
        self.main_layout.setObjectName(u"main_layout")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.main_layout.sizePolicy().hasHeightForWidth())
        self.main_layout.setSizePolicy(sizePolicy)
        self.verticalLayout_2 = QVBoxLayout(self.main_layout)
        self.verticalLayout_2.setSpacing(6)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.stream_buttons = QWidget(self.main_layout)
        self.stream_buttons.setObjectName(u"stream_buttons")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.stream_buttons.sizePolicy().hasHeightForWidth())
        self.stream_buttons.setSizePolicy(sizePolicy1)
        self.stream_buttons.setMaximumSize(QSize(16777215, 40))
        self.horizontalLayout_5 = QHBoxLayout(self.stream_buttons)
        self.horizontalLayout_5.setSpacing(4)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.start_button = QPushButton(self.stream_buttons)
        self.start_button.setObjectName(u"start_button")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.start_button.sizePolicy().hasHeightForWidth())
        self.start_button.setSizePolicy(sizePolicy2)
        self.start_button.setMinimumSize(QSize(0, 40))
        self.start_button.setMaximumSize(QSize(16777215, 40))

        self.horizontalLayout_5.addWidget(self.start_button)

        self.stop_button = QPushButton(self.stream_buttons)
        self.stop_button.setObjectName(u"stop_button")
        sizePolicy2.setHeightForWidth(self.stop_button.sizePolicy().hasHeightForWidth())
        self.stop_button.setSizePolicy(sizePolicy2)
        self.stop_button.setMinimumSize(QSize(0, 40))
        self.stop_button.setMaximumSize(QSize(16777215, 40))

        self.horizontalLayout_5.addWidget(self.stop_button)


        self.verticalLayout_2.addWidget(self.stream_buttons)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.label = QLabel(self.main_layout)
        self.label.setObjectName(u"label")
        self.label.setMaximumSize(QSize(16777215, 40))

        self.verticalLayout_4.addWidget(self.label)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(50)
        self.gridLayout.setContentsMargins(0, -1, -1, -1)

        self.verticalLayout_4.addLayout(self.gridLayout)


        self.verticalLayout_2.addLayout(self.verticalLayout_4)


        self.verticalLayout.addWidget(self.main_layout)


        self.retranslateUi(StreamDialog)

        QMetaObject.connectSlotsByName(StreamDialog)
    # setupUi

    def retranslateUi(self, StreamDialog):
        StreamDialog.setWindowTitle(QCoreApplication.translate("StreamDialog", u"View Stream", None))
        self.view_stream_label.setText(QCoreApplication.translate("StreamDialog", u"View stream", None))
        self.device_box.setPlaceholderText(QCoreApplication.translate("StreamDialog", u"Select bluetooth device", None))
#if QT_CONFIG(tooltip)
        self.refresh_button.setToolTip(QCoreApplication.translate("StreamDialog", u"<html><head/><body><p>Refresh the list of samples</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.refresh_button.setText(QCoreApplication.translate("StreamDialog", u"Refresh", None))
        self.start_button.setText(QCoreApplication.translate("StreamDialog", u"Start streaming", None))
        self.stop_button.setText(QCoreApplication.translate("StreamDialog", u"Stop streaming", None))
        self.label.setText(QCoreApplication.translate("StreamDialog", u"Found sensors (greyed out if no data was received yet):", None))
    # retranslateUi

