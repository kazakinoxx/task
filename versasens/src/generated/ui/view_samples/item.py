# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'item.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_SamplesListItem(object):
    def setupUi(self, SamplesListItem):
        if not SamplesListItem.objectName():
            SamplesListItem.setObjectName(u"SamplesListItem")
        SamplesListItem.resize(693, 50)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SamplesListItem.sizePolicy().hasHeightForWidth())
        SamplesListItem.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(SamplesListItem)
        self.horizontalLayout.setSpacing(20)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.timestamp_label = QLabel(SamplesListItem)
        self.timestamp_label.setObjectName(u"timestamp_label")
        sizePolicy.setHeightForWidth(self.timestamp_label.sizePolicy().hasHeightForWidth())
        self.timestamp_label.setSizePolicy(sizePolicy)
        self.timestamp_label.setMaximumSize(QSize(16777215, 16777215))

        self.horizontalLayout.addWidget(self.timestamp_label)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")

        self.horizontalLayout.addLayout(self.verticalLayout)


        self.retranslateUi(SamplesListItem)

        QMetaObject.connectSlotsByName(SamplesListItem)
    # setupUi

    def retranslateUi(self, SamplesListItem):
        SamplesListItem.setWindowTitle("")
        self.timestamp_label.setText(QCoreApplication.translate("SamplesListItem", u"01.01.1999 at 12:12:12", None))
    # retranslateUi

