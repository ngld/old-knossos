# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'modinfo.ui'
#
# Created: Wed Nov  5 01:32:41 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from ..qt import QtCore, QtGui

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
        self.tabs = QtGui.QTabWidget(Dialog)
        self.tabs.setObjectName("tabs")
        self.tab = QtGui.QWidget()
        self.tab.setObjectName("tab")
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.tab)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.desc = QtGui.QPlainTextEdit(self.tab)
        self.desc.setReadOnly(True)
        self.desc.setObjectName("desc")
        self.verticalLayout_3.addWidget(self.desc)
        self.tabs.addTab(self.tab, "")
        self.tab_2 = QtGui.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.tab_2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.note = QtGui.QPlainTextEdit(self.tab_2)
        self.note.setReadOnly(True)
        self.note.setObjectName("note")
        self.verticalLayout_2.addWidget(self.note)
        self.tabs.addTab(self.tab_2, "")
        self.verticalLayout.addWidget(self.tabs)
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
        self.tabs.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Mod", None, QtGui.QApplication.UnicodeUTF8))
        self.modname.setText(QtGui.QApplication.translate("Dialog", "Mod name 1.0", None, QtGui.QApplication.UnicodeUTF8))
        self.logo.setText(QtGui.QApplication.translate("Dialog", "TextLabel", None, QtGui.QApplication.UnicodeUTF8))
        self.tabs.setTabText(self.tabs.indexOf(self.tab), QtGui.QApplication.translate("Dialog", "Description", None, QtGui.QApplication.UnicodeUTF8))
        self.tabs.setTabText(self.tabs.indexOf(self.tab_2), QtGui.QApplication.translate("Dialog", "Notes", None, QtGui.QApplication.UnicodeUTF8))
        self.runButton.setText(QtGui.QApplication.translate("Dialog", "Launch", None, QtGui.QApplication.UnicodeUTF8))
        self.settingsButton.setText(QtGui.QApplication.translate("Dialog", "Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.closeButton.setText(QtGui.QApplication.translate("Dialog", "Close", None, QtGui.QApplication.UnicodeUTF8))

