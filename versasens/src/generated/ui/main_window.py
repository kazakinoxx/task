# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.setEnabled(True)
        MainWindow.resize(597, 440)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.header = QWidget(self.centralwidget)
        self.header.setObjectName(u"header")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.header.sizePolicy().hasHeightForWidth())
        self.header.setSizePolicy(sizePolicy1)
        self.header.setMinimumSize(QSize(0, 30))
        self.header.setMaximumSize(QSize(16777215, 50))
        self.horizontalLayout = QHBoxLayout(self.header)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, 0, -1, 0)
        self.header_title = QLabel(self.header)
        self.header_title.setObjectName(u"header_title")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.header_title.setFont(font)

        self.horizontalLayout.addWidget(self.header_title)

        self.header_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.header_spacer)

        self.settings_button = QPushButton(self.header)
        self.settings_button.setObjectName(u"settings_button")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.settings_button.sizePolicy().hasHeightForWidth())
        self.settings_button.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.settings_button)


        self.verticalLayout.addWidget(self.header)

        self.center_layout = QHBoxLayout()
        self.center_layout.setSpacing(6)
        self.center_layout.setObjectName(u"center_layout")
        self.center_widget = QWidget(self.centralwidget)
        self.center_widget.setObjectName(u"center_widget")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.center_widget.sizePolicy().hasHeightForWidth())
        self.center_widget.setSizePolicy(sizePolicy3)
        self.verticalLayout_3 = QVBoxLayout(self.center_widget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.buttons = QWidget(self.center_widget)
        self.buttons.setObjectName(u"buttons")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.buttons.sizePolicy().hasHeightForWidth())
        self.buttons.setSizePolicy(sizePolicy4)
        self.buttons.setMinimumSize(QSize(0, 0))
        self.verticalLayout_2 = QVBoxLayout(self.buttons)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.add_button = QPushButton(self.buttons)
        self.add_button.setObjectName(u"add_button")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.add_button.sizePolicy().hasHeightForWidth())
        self.add_button.setSizePolicy(sizePolicy5)
        self.add_button.setMinimumSize(QSize(200, 54))
        self.add_button.setMaximumSize(QSize(200, 54))
        self.add_button.setBaseSize(QSize(0, 0))
        self.add_button.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.verticalLayout_2.addWidget(self.add_button)

        self.stream_button = QPushButton(self.buttons)
        self.stream_button.setObjectName(u"stream_button")
        sizePolicy5.setHeightForWidth(self.stream_button.sizePolicy().hasHeightForWidth())
        self.stream_button.setSizePolicy(sizePolicy5)
        self.stream_button.setMinimumSize(QSize(200, 54))
        self.stream_button.setMaximumSize(QSize(200, 54))

        self.verticalLayout_2.addWidget(self.stream_button)

        self.view_button = QPushButton(self.buttons)
        self.view_button.setObjectName(u"view_button")
        sizePolicy5.setHeightForWidth(self.view_button.sizePolicy().hasHeightForWidth())
        self.view_button.setSizePolicy(sizePolicy5)
        self.view_button.setMinimumSize(QSize(200, 54))
        self.view_button.setMaximumSize(QSize(200, 54))

        self.verticalLayout_2.addWidget(self.view_button)


        self.verticalLayout_3.addWidget(self.buttons)


        self.center_layout.addWidget(self.center_widget)


        self.verticalLayout.addLayout(self.center_layout)

        self.footer = QWidget(self.centralwidget)
        self.footer.setObjectName(u"footer")
        sizePolicy1.setHeightForWidth(self.footer.sizePolicy().hasHeightForWidth())
        self.footer.setSizePolicy(sizePolicy1)
        self.footer.setMinimumSize(QSize(0, 30))
        self.horizontalLayout_2 = QHBoxLayout(self.footer)
        self.horizontalLayout_2.setSpacing(30)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(9, 0, 9, 0)
        self.last_added_text = QLabel(self.footer)
        self.last_added_text.setObjectName(u"last_added_text")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.last_added_text.sizePolicy().hasHeightForWidth())
        self.last_added_text.setSizePolicy(sizePolicy6)
        font1 = QFont()
        font1.setBold(True)
        self.last_added_text.setFont(font1)

        self.horizontalLayout_2.addWidget(self.last_added_text)

        self.last_id_text = QLabel(self.footer)
        self.last_id_text.setObjectName(u"last_id_text")

        self.horizontalLayout_2.addWidget(self.last_id_text)

        self.time_ago_text = QLabel(self.footer)
        self.time_ago_text.setObjectName(u"time_ago_text")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(0)
        sizePolicy7.setHeightForWidth(self.time_ago_text.sizePolicy().hasHeightForWidth())
        self.time_ago_text.setSizePolicy(sizePolicy7)
        self.time_ago_text.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.time_ago_text.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.time_ago_text)


        self.verticalLayout.addWidget(self.footer)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"VersaSens GUI", None))
        self.header_title.setText(QCoreApplication.translate("MainWindow", u"VersaSens", None))
        self.settings_button.setText(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.add_button.setText(QCoreApplication.translate("MainWindow", u"Add new samples", None))
        self.stream_button.setText(QCoreApplication.translate("MainWindow", u"Stream data", None))
        self.view_button.setText(QCoreApplication.translate("MainWindow", u"View samples", None))
        self.last_added_text.setText(QCoreApplication.translate("MainWindow", u"Last added:", None))
        self.last_id_text.setText(QCoreApplication.translate("MainWindow", u"PLACEHOLDER", None))
        self.time_ago_text.setText(QCoreApplication.translate("MainWindow", u"(time ago)", None))
    # retranslateUi

