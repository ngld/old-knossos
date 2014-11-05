# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings_sources.ui'
#
# Created: Wed Nov  5 01:32:43 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from ..qt import QtCore, QtGui

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 300)
        self.verticalLayout = QtGui.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.sourceList = QtGui.QListWidget(Form)
        self.sourceList.setDragEnabled(True)
        self.sourceList.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.sourceList.setObjectName("sourceList")
        self.verticalLayout.addWidget(self.sourceList)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.addSource = QtGui.QPushButton(Form)
        self.addSource.setObjectName("addSource")
        self.horizontalLayout.addWidget(self.addSource)
        self.editSource = QtGui.QPushButton(Form)
        self.editSource.setObjectName("editSource")
        self.horizontalLayout.addWidget(self.editSource)
        self.removeSource = QtGui.QPushButton(Form)
        self.removeSource.setObjectName("removeSource")
        self.horizontalLayout.addWidget(self.removeSource)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.addSource.setText(QtGui.QApplication.translate("Form", "Add", None, QtGui.QApplication.UnicodeUTF8))
        self.editSource.setText(QtGui.QApplication.translate("Form", "Edit", None, QtGui.QApplication.UnicodeUTF8))
        self.removeSource.setText(QtGui.QApplication.translate("Form", "Remove", None, QtGui.QApplication.UnicodeUTF8))

