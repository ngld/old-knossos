# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings2.ui'
#
# Created: Wed Nov  5 01:32:42 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from ..qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(575, 400)
        self.layout = QtGui.QHBoxLayout(Dialog)
        self.layout.setObjectName("layout")
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.saveButton = QtGui.QPushButton(Dialog)
        self.saveButton.setObjectName("saveButton")
        self.verticalLayout.addWidget(self.saveButton)
        self.treeWidget = QtGui.QTreeWidget(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeWidget.sizePolicy().hasHeightForWidth())
        self.treeWidget.setSizePolicy(sizePolicy)
        self.treeWidget.setMaximumSize(QtCore.QSize(149, 16777215))
        self.treeWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.treeWidget.setProperty("showDropIndicator", False)
        self.treeWidget.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.treeWidget.setWordWrap(True)
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.setObjectName("treeWidget")
        item_0 = QtGui.QTreeWidgetItem(self.treeWidget)
        item_0 = QtGui.QTreeWidgetItem(self.treeWidget)
        item_0.setFlags(QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_0 = QtGui.QTreeWidgetItem(self.treeWidget)
        item_0.setFlags(QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_1 = QtGui.QTreeWidgetItem(item_0)
        item_0 = QtGui.QTreeWidgetItem(self.treeWidget)
        self.verticalLayout.addWidget(self.treeWidget)
        self.layout.addLayout(self.verticalLayout)
        self.currentTab = QtGui.QWidget(Dialog)
        self.currentTab.setObjectName("currentTab")
        self.layout.addWidget(self.currentTab)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.saveButton.setText(QtGui.QApplication.translate("Dialog", "Save", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.headerItem().setText(0, QtGui.QApplication.translate("Dialog", "1", None, QtGui.QApplication.UnicodeUTF8))
        __sortingEnabled = self.treeWidget.isSortingEnabled()
        self.treeWidget.setSortingEnabled(False)
        self.treeWidget.topLevelItem(0).setText(0, QtGui.QApplication.translate("Dialog", "About Knossos", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(1).setText(0, QtGui.QApplication.translate("Dialog", "Launcher settings", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(1).child(0).setText(0, QtGui.QApplication.translate("Dialog", "Retail install", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(1).child(1).setText(0, QtGui.QApplication.translate("Dialog", "Mod sources", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(1).child(2).setText(0, QtGui.QApplication.translate("Dialog", "Mod versions", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(2).setText(0, QtGui.QApplication.translate("Dialog", "Game settings", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(2).child(0).setText(0, QtGui.QApplication.translate("Dialog", "Video", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(2).child(1).setText(0, QtGui.QApplication.translate("Dialog", "Audio", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(2).child(2).setText(0, QtGui.QApplication.translate("Dialog", "Input", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(2).child(3).setText(0, QtGui.QApplication.translate("Dialog", "Network", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(2).child(4).setText(0, QtGui.QApplication.translate("Dialog", "Default flags", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.topLevelItem(3).setText(0, QtGui.QApplication.translate("Dialog", "Help", None, QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.setSortingEnabled(__sortingEnabled)

