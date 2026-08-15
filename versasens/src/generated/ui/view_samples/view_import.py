# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'view_import.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QGridLayout,
    QLabel, QListWidget, QListWidgetItem, QSizePolicy,
    QTextBrowser, QVBoxLayout, QWidget)

class Ui_ViewImportDialog(object):
    def setupUi(self, ViewImportDialog):
        if not ViewImportDialog.objectName():
            ViewImportDialog.setObjectName(u"ViewImportDialog")
        ViewImportDialog.resize(601, 657)
        self.verticalLayout_2 = QVBoxLayout(ViewImportDialog)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(ViewImportDialog)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMaximumSize(QSize(100, 16777215))

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.id_label = QLabel(ViewImportDialog)
        self.id_label.setObjectName(u"id_label")
        font = QFont()
        font.setBold(True)
        self.id_label.setFont(font)

        self.gridLayout.addWidget(self.id_label, 0, 1, 1, 1)

        self.label_4 = QLabel(ViewImportDialog)
        self.label_4.setObjectName(u"label_4")
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)
        self.label_4.setMaximumSize(QSize(100, 16777215))

        self.gridLayout.addWidget(self.label_4, 1, 0, 1, 1)

        self.timestamp_label = QLabel(ViewImportDialog)
        self.timestamp_label.setObjectName(u"timestamp_label")
        self.timestamp_label.setFont(font)

        self.gridLayout.addWidget(self.timestamp_label, 1, 1, 1, 1)


        self.verticalLayout_2.addLayout(self.gridLayout)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_3 = QLabel(ViewImportDialog)
        self.label_3.setObjectName(u"label_3")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy1)
        self.label_3.setMaximumSize(QSize(16777215, 22))

        self.verticalLayout.addWidget(self.label_3)

        self.notes_text = QTextBrowser(ViewImportDialog)
        self.notes_text.setObjectName(u"notes_text")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.notes_text.sizePolicy().hasHeightForWidth())
        self.notes_text.setSizePolicy(sizePolicy2)
        self.notes_text.setMaximumSize(QSize(16777215, 150))

        self.verticalLayout.addWidget(self.notes_text)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.line = QFrame(ViewImportDialog)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_2.addWidget(self.line)

        self.samples_list = QListWidget(ViewImportDialog)
        self.samples_list.setObjectName(u"samples_list")
        self.samples_list.setSpacing(2)

        self.verticalLayout_2.addWidget(self.samples_list)


        self.retranslateUi(ViewImportDialog)

        QMetaObject.connectSlotsByName(ViewImportDialog)
    # setupUi

    def retranslateUi(self, ViewImportDialog):
        ViewImportDialog.setWindowTitle(QCoreApplication.translate("ViewImportDialog", u"View import", None))
        self.label.setText(QCoreApplication.translate("ViewImportDialog", u"Subject ID:", None))
        self.id_label.setText(QCoreApplication.translate("ViewImportDialog", u"ID", None))
        self.label_4.setText(QCoreApplication.translate("ViewImportDialog", u"Import time:", None))
        self.timestamp_label.setText(QCoreApplication.translate("ViewImportDialog", u"Timestamp", None))
        self.label_3.setText(QCoreApplication.translate("ViewImportDialog", u"Notes", None))
        self.notes_text.setPlaceholderText(QCoreApplication.translate("ViewImportDialog", u"No notes found", None))
    # retranslateUi

