# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'gogextract.ui'
#
# Created: Wed Nov  5 01:32:41 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from ..qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(394, 167)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_3 = QtGui.QLabel(Dialog)
        self.label_3.setWordWrap(True)
        self.label_3.setObjectName("label_3")
        self.verticalLayout.addWidget(self.label_3)
        self.gridLayout_2 = QtGui.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.destPath = QtGui.QLineEdit(Dialog)
        self.destPath.setObjectName("destPath")
        self.gridLayout_2.addWidget(self.destPath, 6, 1, 1, 1)
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName("label")
        self.gridLayout_2.addWidget(self.label, 3, 0, 1, 1)
        self.label_2 = QtGui.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout_2.addWidget(self.label_2, 6, 0, 1, 1)
        self.gogPath = QtGui.QLineEdit(Dialog)
        self.gogPath.setObjectName("gogPath")
        self.gridLayout_2.addWidget(self.gogPath, 3, 1, 1, 1)
        self.gogButton = QtGui.QPushButton(Dialog)
        self.gogButton.setObjectName("gogButton")
        self.gridLayout_2.addWidget(self.gogButton, 3, 2, 1, 1)
        self.destButton = QtGui.QPushButton(Dialog)
        self.destButton.setObjectName("destButton")
        self.gridLayout_2.addWidget(self.destButton, 6, 2, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout_2)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.cancelButton = QtGui.QPushButton(Dialog)
        self.cancelButton.setObjectName("cancelButton")
        self.horizontalLayout.addWidget(self.cancelButton)
        self.installButton = QtGui.QPushButton(Dialog)
        self.installButton.setEnabled(False)
        self.installButton.setObjectName("installButton")
        self.horizontalLayout.addWidget(self.installButton)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Extract from GOG Installer", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Dialog", "Please select the installer which you downloaded from GOG and a destination directory where FS2 should be installed.", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "GOG Installer:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Dialog", "Destination:", None, QtGui.QApplication.UnicodeUTF8))
        self.gogButton.setText(QtGui.QApplication.translate("Dialog", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.destButton.setText(QtGui.QApplication.translate("Dialog", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.cancelButton.setText(QtGui.QApplication.translate("Dialog", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.installButton.setText(QtGui.QApplication.translate("Dialog", "Install", None, QtGui.QApplication.UnicodeUTF8))

