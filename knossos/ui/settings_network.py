# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings_network.ui'
#
# Created: Wed Nov  5 01:32:42 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from ..qt import QtCore, QtGui

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 300)
        self.formLayout = QtGui.QFormLayout(Form)
        self.formLayout.setObjectName("formLayout")
        self.label = QtGui.QLabel(Form)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.label_2 = QtGui.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.label_3 = QtGui.QLabel(Form)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_3)
        self.label_4 = QtGui.QLabel(Form)
        self.label_4.setObjectName("label_4")
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.label_4)
        self.connectionType = QtGui.QComboBox(Form)
        self.connectionType.setObjectName("connectionType")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.connectionType)
        self.connectionSpeed = QtGui.QComboBox(Form)
        self.connectionSpeed.setObjectName("connectionSpeed")
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.connectionSpeed)
        self.localPort = QtGui.QLineEdit(Form)
        self.localPort.setObjectName("localPort")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.localPort)
        self.forceAddress = QtGui.QLineEdit(Form)
        self.forceAddress.setObjectName("forceAddress")
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.forceAddress)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Form", "Connection type: ", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Form", "Connection speed: ", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Form", "Force local port: ", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("Form", "Force IP address: ", None, QtGui.QApplication.UnicodeUTF8))

