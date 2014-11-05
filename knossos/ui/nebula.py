# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'nebula.ui'
#
# Created: Wed Nov  5 01:32:42 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from ..qt import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1067, 686)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.modlistButton = QtGui.QPushButton(self.centralwidget)
        self.modlistButton.setFlat(True)
        self.modlistButton.setObjectName("modlistButton")
        self.horizontalLayout.addWidget(self.modlistButton)
        self.nebulaButton = QtGui.QPushButton(self.centralwidget)
        self.nebulaButton.setFlat(True)
        self.nebulaButton.setObjectName("nebulaButton")
        self.horizontalLayout.addWidget(self.nebulaButton)
        self.fsoSettingsButton = QtGui.QPushButton(self.centralwidget)
        self.fsoSettingsButton.setFlat(True)
        self.fsoSettingsButton.setObjectName("fsoSettingsButton")
        self.horizontalLayout.addWidget(self.fsoSettingsButton)
        self.settingsButton = QtGui.QPushButton(self.centralwidget)
        self.settingsButton.setFlat(True)
        self.settingsButton.setObjectName("settingsButton")
        self.horizontalLayout.addWidget(self.settingsButton)
        self.modtreeButton = QtGui.QPushButton(self.centralwidget)
        self.modtreeButton.setFlat(True)
        self.modtreeButton.setObjectName("modtreeButton")
        self.horizontalLayout.addWidget(self.modtreeButton)
        self.aboutButton = QtGui.QPushButton(self.centralwidget)
        self.aboutButton.setFlat(True)
        self.aboutButton.setObjectName("aboutButton")
        self.horizontalLayout.addWidget(self.aboutButton)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.line = QtGui.QFrame(self.centralwidget)
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout.addWidget(self.line)
        self.webView = QtWebKit.QWebView(self.centralwidget)
        self.webView.setUrl(QtCore.QUrl("about:blank"))
        self.webView.setObjectName("webView")
        self.verticalLayout.addWidget(self.webView)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1067, 19))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "fs2mod-py", None, QtGui.QApplication.UnicodeUTF8))
        self.modlistButton.setText(QtGui.QApplication.translate("MainWindow", "Mod List", None, QtGui.QApplication.UnicodeUTF8))
        self.nebulaButton.setText(QtGui.QApplication.translate("MainWindow", "Nebula", None, QtGui.QApplication.UnicodeUTF8))
        self.fsoSettingsButton.setText(QtGui.QApplication.translate("MainWindow", "FSO Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.settingsButton.setText(QtGui.QApplication.translate("MainWindow", "Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.modtreeButton.setText(QtGui.QApplication.translate("MainWindow", "Mod Tree", None, QtGui.QApplication.UnicodeUTF8))
        self.aboutButton.setText(QtGui.QApplication.translate("MainWindow", "About", None, QtGui.QApplication.UnicodeUTF8))

from ..qt import QtWebKit
