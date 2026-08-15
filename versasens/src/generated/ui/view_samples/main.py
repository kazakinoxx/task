# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
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
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_ViewSamplesDialog(object):
    def setupUi(self, ViewSamplesDialog):
        if not ViewSamplesDialog.objectName():
            ViewSamplesDialog.setObjectName(u"ViewSamplesDialog")
        ViewSamplesDialog.resize(441, 450)
        self.verticalLayout = QVBoxLayout(ViewSamplesDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget = QWidget(ViewSamplesDialog)
        self.widget.setObjectName(u"widget")
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, -1)
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.open_db_button = QPushButton(self.widget)
        self.open_db_button.setObjectName(u"open_db_button")

        self.horizontalLayout.addWidget(self.open_db_button)

        self.refresh_button = QPushButton(self.widget)
        self.refresh_button.setObjectName(u"refresh_button")

        self.horizontalLayout.addWidget(self.refresh_button)


        self.verticalLayout.addWidget(self.widget)

        self.widget_2 = QWidget(ViewSamplesDialog)
        self.widget_2.setObjectName(u"widget_2")
        font = QFont()
        font.setBold(True)
        self.widget_2.setFont(font)
        self.horizontalLayout_2 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 0, -1, -1)
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)

        self.label_2 = QLabel(self.widget_2)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_2.addWidget(self.label_2)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_3)


        self.verticalLayout.addWidget(self.widget_2)

        self.scrollArea = QScrollArea(ViewSamplesDialog)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.ids_contents = QWidget()
        self.ids_contents.setObjectName(u"ids_contents")
        self.ids_contents.setGeometry(QRect(0, 0, 421, 356))
        self.ids_layout = QVBoxLayout(self.ids_contents)
        self.ids_layout.setSpacing(2)
        self.ids_layout.setObjectName(u"ids_layout")
        self.scrollArea.setWidget(self.ids_contents)

        self.verticalLayout.addWidget(self.scrollArea)


        self.retranslateUi(ViewSamplesDialog)

        QMetaObject.connectSlotsByName(ViewSamplesDialog)
    # setupUi

    def retranslateUi(self, ViewSamplesDialog):
        ViewSamplesDialog.setWindowTitle(QCoreApplication.translate("ViewSamplesDialog", u"View Samples", None))
        self.label.setText(QCoreApplication.translate("ViewSamplesDialog", u"View samples", None))
#if QT_CONFIG(tooltip)
        self.open_db_button.setToolTip(QCoreApplication.translate("ViewSamplesDialog", u"<html><head/><body><p>Open the database folder in explorer</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_db_button.setText(QCoreApplication.translate("ViewSamplesDialog", u"Open database folder", None))
#if QT_CONFIG(tooltip)
        self.refresh_button.setToolTip(QCoreApplication.translate("ViewSamplesDialog", u"<html><head/><body><p>Refresh the list of samples</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.refresh_button.setText(QCoreApplication.translate("ViewSamplesDialog", u"Refresh", None))
        self.label_2.setText(QCoreApplication.translate("ViewSamplesDialog", u"Subject IDs", None))
    # retranslateUi

