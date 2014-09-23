# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'modinfo.ui'
#
# Created: Tue Sep 23 22:16:20 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from lib.qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(377, 552)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.modname = QtGui.QLabel(Dialog)
        font = QtGui.QFont()
        font.setPointSize(13)
        font.setWeight(75)
        font.setBold(True)
        self.modname.setFont(font)
        self.modname.setAlignment(QtCore.Qt.AlignCenter)
        self.modname.setWordWrap(True)
        self.modname.setObjectName("modname")
        self.verticalLayout.addWidget(self.modname)
        self.logo = QtGui.QLabel(Dialog)
        self.logo.setMinimumSize(QtCore.QSize(255, 112))
        self.logo.setAlignment(QtCore.Qt.AlignCenter)
        self.logo.setObjectName("logo")
        self.verticalLayout.addWidget(self.logo)
        self.label = QtGui.QLabel(Dialog)
        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.desc = QtGui.QPlainTextEdit(Dialog)
        self.desc.setReadOnly(True)
        self.desc.setObjectName("desc")
        self.verticalLayout.addWidget(self.desc)
        self.label_3 = QtGui.QLabel(Dialog)
        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.verticalLayout.addWidget(self.label_3)
        self.note = QtGui.QPlainTextEdit(Dialog)
        self.note.setReadOnly(True)
        self.note.setObjectName("note")
        self.verticalLayout.addWidget(self.note)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.runButton = QtGui.QPushButton(Dialog)
        self.runButton.setObjectName("runButton")
        self.horizontalLayout.addWidget(self.runButton)
        self.settingsButton = QtGui.QPushButton(Dialog)
        self.settingsButton.setObjectName("settingsButton")
        self.horizontalLayout.addWidget(self.settingsButton)
        self.closeButton = QtGui.QPushButton(Dialog)
        self.closeButton.setObjectName("closeButton")
        self.horizontalLayout.addWidget(self.closeButton)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Mod", None, QtGui.QApplication.UnicodeUTF8))
        self.modname.setText(QtGui.QApplication.translate("Dialog", "Mod name 1.0", None, QtGui.QApplication.UnicodeUTF8))
        self.logo.setText(QtGui.QApplication.translate("Dialog", "TextLabel", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Description", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Dialog", "Notes", None, QtGui.QApplication.UnicodeUTF8))
        self.runButton.setText(QtGui.QApplication.translate("Dialog", "Launch", None, QtGui.QApplication.UnicodeUTF8))
        self.settingsButton.setText(QtGui.QApplication.translate("Dialog", "Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.closeButton.setText(QtGui.QApplication.translate("Dialog", "Close", None, QtGui.QApplication.UnicodeUTF8))

