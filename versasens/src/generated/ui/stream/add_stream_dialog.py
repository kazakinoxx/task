# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_stream_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QHBoxLayout, QLabel, QLineEdit, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_AddStreamDialog(object):
    def setupUi(self, AddStreamDialog):
        if not AddStreamDialog.objectName():
            AddStreamDialog.setObjectName(u"AddStreamDialog")
        AddStreamDialog.setEnabled(True)
        AddStreamDialog.resize(400, 300)
        self.verticalLayout = QVBoxLayout(AddStreamDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(AddStreamDialog)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.patient_layout = QHBoxLayout()
        self.patient_layout.setObjectName(u"patient_layout")
        self.patient_label = QLabel(AddStreamDialog)
        self.patient_label.setObjectName(u"patient_label")
        self.patient_label.setMinimumSize(QSize(100, 0))

        self.patient_layout.addWidget(self.patient_label)

        self.patient_input = QLineEdit(AddStreamDialog)
        self.patient_input.setObjectName(u"patient_input")

        self.patient_layout.addWidget(self.patient_input)


        self.verticalLayout.addLayout(self.patient_layout)

        self.notes_layout = QVBoxLayout()
        self.notes_layout.setObjectName(u"notes_layout")
        self.notes_layout.setContentsMargins(0, 5, -1, -1)
        self.notes_label = QLabel(AddStreamDialog)
        self.notes_label.setObjectName(u"notes_label")

        self.notes_layout.addWidget(self.notes_label)

        self.notes_input = QTextEdit(AddStreamDialog)
        self.notes_input.setObjectName(u"notes_input")

        self.notes_layout.addWidget(self.notes_input)


        self.verticalLayout.addLayout(self.notes_layout)

        self.buttonBox = QDialogButtonBox(AddStreamDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(AddStreamDialog)

        QMetaObject.connectSlotsByName(AddStreamDialog)
    # setupUi

    def retranslateUi(self, AddStreamDialog):
        AddStreamDialog.setWindowTitle(QCoreApplication.translate("AddStreamDialog", u"Add New Stream Samples", None))
        self.label.setText(QCoreApplication.translate("AddStreamDialog", u"Enter information to import stream data:", None))
        self.patient_label.setText(QCoreApplication.translate("AddStreamDialog", u"Subject ID", None))
        self.patient_input.setPlaceholderText(QCoreApplication.translate("AddStreamDialog", u"Enter subject ID", None))
        self.notes_label.setText(QCoreApplication.translate("AddStreamDialog", u"Notes", None))
        self.notes_input.setPlaceholderText(QCoreApplication.translate("AddStreamDialog", u"Enter notes", None))
    # retranslateUi

