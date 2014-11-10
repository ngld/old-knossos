# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'progress.ui'
#
# Created: Wed Nov  5 01:32:42 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from ..qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        Dialog.resize(594, 443)
        Dialog.setCursor(QtCore.Qt.BusyCursor)
        Dialog.setModal(True)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.progressBar = QtGui.QProgressBar(Dialog)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName("progressBar")
        self.verticalLayout.addWidget(self.progressBar)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_2 = QtGui.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.hideButton = QtGui.QPushButton(Dialog)
        self.hideButton.setObjectName("hideButton")
        self.horizontalLayout.addWidget(self.hideButton)
        self.abortButton = QtGui.QPushButton(Dialog)
        self.abortButton.setObjectName("abortButton")
        self.horizontalLayout.addWidget(self.abortButton)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.tasksArea = QtGui.QScrollArea(Dialog)
        self.tasksArea.setWidgetResizable(True)
        self.tasksArea.setObjectName("tasksArea")
        self.tasks = QtGui.QWidget()
        self.tasks.setGeometry(QtCore.QRect(0, 0, 576, 351))
        self.tasks.setObjectName("tasks")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.tasks)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem1)
        self.tasksArea.setWidget(self.tasks)
        self.verticalLayout.addWidget(self.tasksArea)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Working...", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "TextLabel", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Dialog", "Tasks", None, QtGui.QApplication.UnicodeUTF8))
        self.hideButton.setText(QtGui.QApplication.translate("Dialog", "Hide", None, QtGui.QApplication.UnicodeUTF8))
        self.abortButton.setText(QtGui.QApplication.translate("Dialog", "Cancel", None, QtGui.QApplication.UnicodeUTF8))

