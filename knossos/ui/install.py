# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'install.ui'
#
# Created: Wed Nov  5 01:32:41 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from ..qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        Dialog.resize(301, 287)
        Dialog.setModal(True)
        self.verticalLayout_2 = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.titleLabel = QtGui.QLabel(Dialog)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setWeight(75)
        font.setBold(True)
        self.titleLabel.setFont(font)
        self.titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.titleLabel.setObjectName("titleLabel")
        self.verticalLayout_2.addWidget(self.titleLabel)
        spacerItem = QtGui.QSpacerItem(40, 10, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Preferred)
        self.verticalLayout_2.addItem(spacerItem)
        self.depsLabel = QtGui.QLabel(Dialog)
        self.depsLabel.setObjectName("depsLabel")
        self.verticalLayout_2.addWidget(self.depsLabel)
        self.pkgsLayout = QtGui.QVBoxLayout()
        self.pkgsLayout.setObjectName("pkgsLayout")
        self.verticalLayout_2.addLayout(self.pkgsLayout)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem1)
        self.dlSizeLabel = QtGui.QLabel(Dialog)
        self.dlSizeLabel.setObjectName("dlSizeLabel")
        self.verticalLayout_2.addWidget(self.dlSizeLabel)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.installButton = QtGui.QPushButton(Dialog)
        self.installButton.setObjectName("installButton")
        self.horizontalLayout.addWidget(self.installButton)
        self.cancelButton = QtGui.QPushButton(Dialog)
        self.cancelButton.setObjectName("cancelButton")
        self.horizontalLayout.addWidget(self.cancelButton)
        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Install a mod", None, QtGui.QApplication.UnicodeUTF8))
        self.titleLabel.setText(QtGui.QApplication.translate("Dialog", "Install {MOD}?", None, QtGui.QApplication.UnicodeUTF8))
        self.depsLabel.setText(QtGui.QApplication.translate("Dialog", "{DEPS} will also be installed.", None, QtGui.QApplication.UnicodeUTF8))
        self.dlSizeLabel.setText(QtGui.QApplication.translate("Dialog", "Download size: {DL_SIZE}", None, QtGui.QApplication.UnicodeUTF8))
        self.installButton.setText(QtGui.QApplication.translate("Dialog", "Install", None, QtGui.QApplication.UnicodeUTF8))
        self.cancelButton.setText(QtGui.QApplication.translate("Dialog", "Cancel", None, QtGui.QApplication.UnicodeUTF8))

