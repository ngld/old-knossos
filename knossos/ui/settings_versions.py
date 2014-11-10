# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings_versions.ui'
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
        self.allModVersions = QtGui.QCheckBox(Form)
        self.allModVersions.setObjectName("allModVersions")
        self.verticalLayout.addWidget(self.allModVersions)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.allModVersions.setText(QtGui.QApplication.translate("Form", "Show all mod versions", None, QtGui.QApplication.UnicodeUTF8))

