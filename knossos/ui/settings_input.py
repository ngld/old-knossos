# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings_input.ui'
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
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label)
        self.keyLayout = QtGui.QComboBox(Form)
        self.keyLayout.setObjectName("keyLayout")
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.keyLayout)
        self.useSetxkbmap = QtGui.QCheckBox(Form)
        self.useSetxkbmap.setObjectName("useSetxkbmap")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.useSetxkbmap)
        self.label_2 = QtGui.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_2)
        self.controller = QtGui.QComboBox(Form)
        self.controller.setObjectName("controller")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.controller)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Form", "Layout: ", None, QtGui.QApplication.UnicodeUTF8))
        self.useSetxkbmap.setText(QtGui.QApplication.translate("Form", "Use \"setxkbmap\"", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Form", "Controller: ", None, QtGui.QApplication.UnicodeUTF8))

