# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mod_settings.ui'
#
# Created: Thu Nov 20 21:22:56 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from ..qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(457, 587)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tabWidget = QtGui.QTabWidget(Dialog)
        self.tabWidget.setObjectName("tabWidget")
        self.flagsTab = QtGui.QWidget()
        self.flagsTab.setObjectName("flagsTab")
        self.tabWidget.addTab(self.flagsTab, "")
        self.tab_2 = QtGui.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.tab_2)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.pkgsLayout = QtGui.QVBoxLayout()
        self.pkgsLayout.setObjectName("pkgsLayout")
        self.verticalLayout_3.addLayout(self.pkgsLayout)
        self.dlSizeLabel = QtGui.QLabel(self.tab_2)
        self.dlSizeLabel.setObjectName("dlSizeLabel")
        self.verticalLayout_3.addWidget(self.dlSizeLabel)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem)
        self.applyPkgChanges = QtGui.QPushButton(self.tab_2)
        self.applyPkgChanges.setObjectName("applyPkgChanges")
        self.verticalLayout_3.addWidget(self.applyPkgChanges)
        self.tabWidget.addTab(self.tab_2, "")
        self.verticalLayout.addWidget(self.tabWidget)

        self.retranslateUi(Dialog)
        self.tabWidget.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Mod settings", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.flagsTab), QtGui.QApplication.translate("Dialog", "Flags", None, QtGui.QApplication.UnicodeUTF8))
        self.dlSizeLabel.setText(QtGui.QApplication.translate("Dialog", "Download size: {DL_SIZE}", None, QtGui.QApplication.UnicodeUTF8))
        self.applyPkgChanges.setText(QtGui.QApplication.translate("Dialog", "Apply changes", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QtGui.QApplication.translate("Dialog", "Packages", None, QtGui.QApplication.UnicodeUTF8))

