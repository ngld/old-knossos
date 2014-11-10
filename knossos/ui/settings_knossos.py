# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings_knossos.ui'
#
# Created: Wed Nov  5 01:41:10 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from ..qt import QtCore, QtGui

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
        self.versionLabel = QtGui.QLabel(Form)
        self.versionLabel.setObjectName("versionLabel")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.versionLabel)
        self.label_2 = QtGui.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_2)
        self.maxDownloads = QtGui.QSpinBox(Form)
        self.maxDownloads.setMaximum(5)
        self.maxDownloads.setObjectName("maxDownloads")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.maxDownloads)
        self.label_3 = QtGui.QLabel(Form)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.label_3)
        self.updateChannel = QtGui.QComboBox(Form)
        self.updateChannel.setObjectName("updateChannel")
        self.updateChannel.addItem("")
        self.updateChannel.addItem("")
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.updateChannel)
        self.updateNotify = QtGui.QCheckBox(Form)
        self.updateNotify.setObjectName("updateNotify")
        self.formLayout.setWidget(4, QtGui.QFormLayout.FieldRole, self.updateNotify)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Form", "Version:", None, QtGui.QApplication.UnicodeUTF8))
        self.versionLabel.setText(QtGui.QApplication.translate("Form", "?", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Form", "Parallel downloads:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Form", "Update channel: ", None, QtGui.QApplication.UnicodeUTF8))
        self.updateChannel.setItemText(0, QtGui.QApplication.translate("Form", "stable", None, QtGui.QApplication.UnicodeUTF8))
        self.updateChannel.setItemText(1, QtGui.QApplication.translate("Form", "develop", None, QtGui.QApplication.UnicodeUTF8))
        self.updateNotify.setText(QtGui.QApplication.translate("Form", "Display update notifications", None, QtGui.QApplication.UnicodeUTF8))

