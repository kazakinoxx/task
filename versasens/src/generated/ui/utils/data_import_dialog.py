# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'data_import_dialog.ui'
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
    QProgressBar, QSizePolicy, QVBoxLayout, QWidget)

class Ui_DataImportDialog(object):
    def setupUi(self, DataImportDialog):
        if not DataImportDialog.objectName():
            DataImportDialog.setObjectName(u"DataImportDialog")
        DataImportDialog.resize(415, 114)
        self.verticalLayout = QVBoxLayout(DataImportDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(DataImportDialog)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout.addWidget(self.label)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(DataImportDialog)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.files_bar = QProgressBar(DataImportDialog)
        self.files_bar.setObjectName(u"files_bar")
        self.files_bar.setValue(24)
        self.files_bar.setTextVisible(True)
        self.files_bar.setInvertedAppearance(False)

        self.horizontalLayout.addWidget(self.files_bar)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.cur_file_label = QLabel(DataImportDialog)
        self.cur_file_label.setObjectName(u"cur_file_label")
        self.cur_file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_2.addWidget(self.cur_file_label)

        self.cur_file_bar = QProgressBar(DataImportDialog)
        self.cur_file_bar.setObjectName(u"cur_file_bar")
        self.cur_file_bar.setValue(24)
        self.cur_file_bar.setTextVisible(False)

        self.horizontalLayout_2.addWidget(self.cur_file_bar)

        self.cur_file_bar_label = QLabel(DataImportDialog)
        self.cur_file_bar_label.setObjectName(u"cur_file_bar_label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cur_file_bar_label.sizePolicy().hasHeightForWidth())
        self.cur_file_bar_label.setSizePolicy(sizePolicy)
        self.cur_file_bar_label.setMinimumSize(QSize(50, 0))
        self.cur_file_bar_label.setMaximumSize(QSize(50, 16777215))
        self.cur_file_bar_label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.cur_file_bar_label)


        self.verticalLayout.addLayout(self.horizontalLayout_2)


        self.retranslateUi(DataImportDialog)

        QMetaObject.connectSlotsByName(DataImportDialog)
    # setupUi

    def retranslateUi(self, DataImportDialog):
        DataImportDialog.setWindowTitle(QCoreApplication.translate("DataImportDialog", u"Importing data...", None))
        self.label.setText(QCoreApplication.translate("DataImportDialog", u"Importing files...", None))
        self.label_2.setText(QCoreApplication.translate("DataImportDialog", u"Total files", None))
        self.files_bar.setFormat(QCoreApplication.translate("DataImportDialog", u"%v/%m", None))
        self.cur_file_label.setText(QCoreApplication.translate("DataImportDialog", u"Importing file X...", None))
        self.cur_file_bar.setFormat(QCoreApplication.translate("DataImportDialog", u"%p%", None))
        self.cur_file_bar_label.setText(QCoreApplication.translate("DataImportDialog", u"0.00%", None))
    # retranslateUi

