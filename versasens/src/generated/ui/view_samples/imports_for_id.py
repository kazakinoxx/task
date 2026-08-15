# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'imports_for_id.ui'
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
    QScrollArea, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_ImportsForIDDialog(object):
    def setupUi(self, ImportsForIDDialog):
        if not ImportsForIDDialog.objectName():
            ImportsForIDDialog.setObjectName(u"ImportsForIDDialog")
        ImportsForIDDialog.resize(409, 407)
        self.verticalLayout = QVBoxLayout(ImportsForIDDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget = QWidget(ImportsForIDDialog)
        self.widget.setObjectName(u"widget")
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, -1)
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.label_2 = QLabel(self.widget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.subject_ID = QLabel(self.widget)
        self.subject_ID.setObjectName(u"subject_ID")
        font = QFont()
        font.setBold(True)
        self.subject_ID.setFont(font)

        self.horizontalLayout.addWidget(self.subject_ID)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addWidget(self.widget)

        self.scrollArea = QScrollArea(ImportsForIDDialog)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.imports_list = QWidget()
        self.imports_list.setObjectName(u"imports_list")
        self.imports_list.setGeometry(QRect(0, 0, 389, 352))
        self.imports_layout = QVBoxLayout(self.imports_list)
        self.imports_layout.setObjectName(u"imports_layout")
        self.scrollArea.setWidget(self.imports_list)

        self.verticalLayout.addWidget(self.scrollArea)


        self.retranslateUi(ImportsForIDDialog)

        QMetaObject.connectSlotsByName(ImportsForIDDialog)
    # setupUi

    def retranslateUi(self, ImportsForIDDialog):
        ImportsForIDDialog.setWindowTitle(QCoreApplication.translate("ImportsForIDDialog", u"Subject ID Samples", None))
        self.label_2.setText(QCoreApplication.translate("ImportsForIDDialog", u"Imports for subject:", None))
        self.subject_ID.setText(QCoreApplication.translate("ImportsForIDDialog", u"ID", None))
    # retranslateUi

