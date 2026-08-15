# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'subitem.ui'
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
    QSpacerItem, QWidget)

class Ui_SamplesListSubitem(object):
    def setupUi(self, SamplesListSubitem):
        if not SamplesListSubitem.objectName():
            SamplesListSubitem.setObjectName(u"SamplesListSubitem")
        SamplesListSubitem.resize(779, 50)
        self.horizontalLayout = QHBoxLayout(SamplesListSubitem)
        self.horizontalLayout.setSpacing(20)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, 0, -1, 0)
        self.index_label = QLabel(SamplesListSubitem)
        self.index_label.setObjectName(u"index_label")

        self.horizontalLayout.addWidget(self.index_label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.widget = QWidget(SamplesListSubitem)
        self.widget.setObjectName(u"widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.right_layout = QHBoxLayout(self.widget)
        self.right_layout.setSpacing(0)
        self.right_layout.setObjectName(u"right_layout")
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")

        self.right_layout.addWidget(self.label)

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setObjectName(u"buttons_layout")

        self.right_layout.addLayout(self.buttons_layout)


        self.horizontalLayout.addWidget(self.widget)


        self.retranslateUi(SamplesListSubitem)

        QMetaObject.connectSlotsByName(SamplesListSubitem)
    # setupUi

    def retranslateUi(self, SamplesListSubitem):
        SamplesListSubitem.setWindowTitle("")
        self.index_label.setText(QCoreApplication.translate("SamplesListSubitem", u"Index", None))
        self.label.setText(QCoreApplication.translate("SamplesListSubitem", u"No data found", None))
    # retranslateUi

