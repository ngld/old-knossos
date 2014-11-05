# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings_audio.ui'
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
        self.label_2 = QtGui.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_2)
        self.playbackDevice = QtGui.QComboBox(Form)
        self.playbackDevice.setObjectName("playbackDevice")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.playbackDevice)
        self.label = QtGui.QLabel(Form)
        self.label.setObjectName("label")
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label)
        self.captureDevice = QtGui.QComboBox(Form)
        self.captureDevice.setObjectName("captureDevice")
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.captureDevice)
        self.enableEFX = QtGui.QCheckBox(Form)
        self.enableEFX.setObjectName("enableEFX")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.enableEFX)
        self.label_3 = QtGui.QLabel(Form)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.label_3)
        self.sampleRate = QtGui.QSpinBox(Form)
        self.sampleRate.setMaximum(1000000)
        self.sampleRate.setSingleStep(100)
        self.sampleRate.setObjectName("sampleRate")
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.sampleRate)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Form", "Playback device: ", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Form", "Capture device: ", None, QtGui.QApplication.UnicodeUTF8))
        self.enableEFX.setText(QtGui.QApplication.translate("Form", "Enable EFX", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Form", "Sample rate:", None, QtGui.QApplication.UnicodeUTF8))
        self.sampleRate.setSuffix(QtGui.QApplication.translate("Form", " Hz", None, QtGui.QApplication.UnicodeUTF8))

