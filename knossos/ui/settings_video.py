# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings_video.ui'
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
        self.formLayout = QtGui.QFormLayout(Form)
        self.formLayout.setObjectName("formLayout")
        self.label = QtGui.QLabel(Form)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.resolution = QtGui.QComboBox(Form)
        self.resolution.setObjectName("resolution")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.resolution)
        self.label_2 = QtGui.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.colorDepth = QtGui.QComboBox(Form)
        self.colorDepth.setObjectName("colorDepth")
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.colorDepth)
        self.label_3 = QtGui.QLabel(Form)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_3)
        self.label_4 = QtGui.QLabel(Form)
        self.label_4.setObjectName("label_4")
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.label_4)
        self.label_5 = QtGui.QLabel(Form)
        self.label_5.setObjectName("label_5")
        self.formLayout.setWidget(4, QtGui.QFormLayout.LabelRole, self.label_5)
        self.textureFilter = QtGui.QComboBox(Form)
        self.textureFilter.setObjectName("textureFilter")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.textureFilter)
        self.antialiasing = QtGui.QComboBox(Form)
        self.antialiasing.setObjectName("antialiasing")
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.antialiasing)
        self.anisotropic = QtGui.QComboBox(Form)
        self.anisotropic.setObjectName("anisotropic")
        self.formLayout.setWidget(4, QtGui.QFormLayout.FieldRole, self.anisotropic)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Form", "Resolution: ", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Form", "Color depth: ", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Form", "Texture filter: ", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("Form", "Antialiasing: ", None, QtGui.QApplication.UnicodeUTF8))
        self.label_5.setText(QtGui.QApplication.translate("Form", "Anisotropic filtering: ", None, QtGui.QApplication.UnicodeUTF8))

