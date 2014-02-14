# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'add_repo.ui'
#
# Created: Fri Feb 14 22:09:36 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.1
#
# WARNING! All changes made in this file will be lost!

from qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(364, 140)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.label_2 = QtGui.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.typeJson = QtGui.QRadioButton(Dialog)
        self.typeJson.setObjectName("typeJson")
        self.horizontalLayout_2.addWidget(self.typeJson)
        self.typeFs2mod = QtGui.QRadioButton(Dialog)
        self.typeFs2mod.setChecked(True)
        self.typeFs2mod.setObjectName("typeFs2mod")
        self.horizontalLayout_2.addWidget(self.typeFs2mod)
        self.formLayout.setLayout(0, QtGui.QFormLayout.FieldRole, self.horizontalLayout_2)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.source = QtGui.QLineEdit(Dialog)
        self.source.setObjectName("source")
        self.horizontalLayout_3.addWidget(self.source)
        self.sourceButton = QtGui.QPushButton(Dialog)
        self.sourceButton.setObjectName("sourceButton")
        self.horizontalLayout_3.addWidget(self.sourceButton)
        self.formLayout.setLayout(1, QtGui.QFormLayout.FieldRole, self.horizontalLayout_3)
        self.label_3 = QtGui.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_3)
        self.title = QtGui.QLineEdit(Dialog)
        self.title.setObjectName("title")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.title)
        self.verticalLayout.addLayout(self.formLayout)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.okButton = QtGui.QPushButton(Dialog)
        self.okButton.setDefault(True)
        self.okButton.setObjectName("okButton")
        self.horizontalLayout.addWidget(self.okButton)
        self.cancelButton = QtGui.QPushButton(Dialog)
        self.cancelButton.setObjectName("cancelButton")
        self.horizontalLayout.addWidget(self.cancelButton)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Add a new mod source", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Type:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Dialog", "Source:", None, QtGui.QApplication.UnicodeUTF8))
        self.typeJson.setText(QtGui.QApplication.translate("Dialog", "JSON", None, QtGui.QApplication.UnicodeUTF8))
        self.typeFs2mod.setText(QtGui.QApplication.translate("Dialog", "fs2mod", None, QtGui.QApplication.UnicodeUTF8))
        self.sourceButton.setText(QtGui.QApplication.translate("Dialog", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Dialog", "Title:", None, QtGui.QApplication.UnicodeUTF8))
        self.okButton.setText(QtGui.QApplication.translate("Dialog", "OK", None, QtGui.QApplication.UnicodeUTF8))
        self.cancelButton.setText(QtGui.QApplication.translate("Dialog", "Cancel", None, QtGui.QApplication.UnicodeUTF8))

