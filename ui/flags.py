# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'flags.ui'
#
# Created: Sat Mar  8 03:06:23 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.1
#
# WARNING! All changes made in this file will be lost!

from qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(455, 507)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.cmdLine = QtGui.QPlainTextEdit(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.cmdLine.sizePolicy().hasHeightForWidth())
        self.cmdLine.setSizePolicy(sizePolicy)
        self.cmdLine.setReadOnly(True)
        self.cmdLine.setObjectName("cmdLine")
        self.verticalLayout.addWidget(self.cmdLine)
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.label_2 = QtGui.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_2)
        self.label_3 = QtGui.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_3)
        self.label_4 = QtGui.QLabel(Dialog)
        self.label_4.setObjectName("label_4")
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_4)
        self.customFlags = QtGui.QLineEdit(Dialog)
        self.customFlags.setObjectName("customFlags")
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.customFlags)
        self.easySetup = QtGui.QComboBox(Dialog)
        self.easySetup.setObjectName("easySetup")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.easySetup)
        self.listType = QtGui.QComboBox(Dialog)
        self.listType.setObjectName("listType")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.listType)
        self.verticalLayout.addLayout(self.formLayout)
        self.flagList = QtGui.QListWidget(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(4)
        sizePolicy.setHeightForWidth(self.flagList.sizePolicy().hasHeightForWidth())
        self.flagList.setSizePolicy(sizePolicy)
        self.flagList.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.flagList.setProperty("showDropIndicator", False)
        self.flagList.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.flagList.setObjectName("flagList")
        self.verticalLayout.addWidget(self.flagList)
        self.buttonBox = QtGui.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(True)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), Dialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Mod Flags", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "The complete commandline:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Dialog", "Easy Setup", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Dialog", "Custom Flags", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("Dialog", "List Type", None, QtGui.QApplication.UnicodeUTF8))

