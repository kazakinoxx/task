# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_samples_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_AddSamplesDialog(object):
    def setupUi(self, AddSamplesDialog):
        if not AddSamplesDialog.objectName():
            AddSamplesDialog.setObjectName(u"AddSamplesDialog")
        AddSamplesDialog.setEnabled(True)
        AddSamplesDialog.resize(455, 432)
        self.verticalLayout = QVBoxLayout(AddSamplesDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.gridLayout = QGridLayout()
        self.gridLayout.setSpacing(10)
        self.gridLayout.setObjectName(u"gridLayout")
        self.samples_label = QLabel(AddSamplesDialog)
        self.samples_label.setObjectName(u"samples_label")
        self.samples_label.setMinimumSize(QSize(100, 22))
        self.samples_label.setMaximumSize(QSize(100, 16777215))
        self.samples_label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.samples_label, 0, 0, 1, 1)

        self.files_button = QPushButton(AddSamplesDialog)
        self.files_button.setObjectName(u"files_button")

        self.gridLayout.addWidget(self.files_button, 0, 1, 1, 1)

        self.delete_checkbox = QCheckBox(AddSamplesDialog)
        self.delete_checkbox.setObjectName(u"delete_checkbox")
        self.delete_checkbox.setEnabled(False)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.delete_checkbox.sizePolicy().hasHeightForWidth())
        self.delete_checkbox.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.delete_checkbox, 2, 1, 1, 1)

        self.selected_label = QLabel(AddSamplesDialog)
        self.selected_label.setObjectName(u"selected_label")
        self.selected_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.selected_label, 1, 1, 1, 1)


        self.verticalLayout.addLayout(self.gridLayout)

        self.line = QFrame(AddSamplesDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.patient_layout = QHBoxLayout()
        self.patient_layout.setObjectName(u"patient_layout")
        self.patient_label = QLabel(AddSamplesDialog)
        self.patient_label.setObjectName(u"patient_label")
        self.patient_label.setMinimumSize(QSize(100, 0))

        self.patient_layout.addWidget(self.patient_label)

        self.patient_input = QLineEdit(AddSamplesDialog)
        self.patient_input.setObjectName(u"patient_input")
        self.patient_input.setEnabled(False)

        self.patient_layout.addWidget(self.patient_input)


        self.verticalLayout.addLayout(self.patient_layout)

        self.notes_layout = QVBoxLayout()
        self.notes_layout.setObjectName(u"notes_layout")
        self.notes_layout.setContentsMargins(0, 5, -1, -1)
        self.notes_label = QLabel(AddSamplesDialog)
        self.notes_label.setObjectName(u"notes_label")

        self.notes_layout.addWidget(self.notes_label)

        self.notes_input = QTextEdit(AddSamplesDialog)
        self.notes_input.setObjectName(u"notes_input")
        self.notes_input.setEnabled(False)

        self.notes_layout.addWidget(self.notes_input)


        self.verticalLayout.addLayout(self.notes_layout)

        self.buttonBox = QDialogButtonBox(AddSamplesDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setCenterButtons(False)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(AddSamplesDialog)

        QMetaObject.connectSlotsByName(AddSamplesDialog)
    # setupUi

    def retranslateUi(self, AddSamplesDialog):
        AddSamplesDialog.setWindowTitle(QCoreApplication.translate("AddSamplesDialog", u"Add New Samples", None))
        self.samples_label.setText(QCoreApplication.translate("AddSamplesDialog", u"Samples", None))
        self.files_button.setText(QCoreApplication.translate("AddSamplesDialog", u"Select files...", None))
        self.delete_checkbox.setText(QCoreApplication.translate("AddSamplesDialog", u"Delete files after import", None))
        self.selected_label.setText(QCoreApplication.translate("AddSamplesDialog", u"No files selected", None))
        self.patient_label.setText(QCoreApplication.translate("AddSamplesDialog", u"Subject ID", None))
        self.patient_input.setPlaceholderText(QCoreApplication.translate("AddSamplesDialog", u"Enter subject ID", None))
        self.notes_label.setText(QCoreApplication.translate("AddSamplesDialog", u"Notes", None))
        self.notes_input.setPlaceholderText(QCoreApplication.translate("AddSamplesDialog", u"Enter notes", None))
    # retranslateUi

