# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings_knossos.ui'
#
# Created: Tue Nov  4 00:16:16 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from lib.qt import QtCore, QtGui

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 300)
        self.formLayout = QtGui.QFormLayout(Form)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName("formLayout")
        self.label = QtGui.QLabel(Form)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.label_2 = QtGui.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_2)
        self.versionLabel = QtGui.QLabel(Form)
        self.versionLabel.setObjectName("versionLabel")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.versionLabel)
        self.maxDownloads = QtGui.QSpinBox(Form)
        self.maxDownloads.setObjectName("maxDownloads")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.maxDownloads)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Form", "Version:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Form", "Parallel downloads:", None, QtGui.QApplication.UnicodeUTF8))
        self.versionLabel.setText(QtGui.QApplication.translate("Form", "?", None, QtGui.QApplication.UnicodeUTF8))

