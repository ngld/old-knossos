# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main.ui'
#
# Created: Fri Feb 14 17:33:18 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.1
#
# WARNING! All changes made in this file will be lost!

from qt import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(544, 656)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tabs = QtGui.QTabWidget(self.centralwidget)
        self.tabs.setObjectName("tabs")
        self.fs2 = QtGui.QWidget()
        self.fs2.setObjectName("fs2")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.fs2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        self.gogextract = QtGui.QPushButton(self.fs2)
        self.gogextract.setObjectName("gogextract")
        self.verticalLayout_2.addWidget(self.gogextract)
        self.select = QtGui.QPushButton(self.fs2)
        self.select.setObjectName("select")
        self.verticalLayout_2.addWidget(self.select)
        self.fs2_bin = QtGui.QLabel(self.fs2)
        self.fs2_bin.setObjectName("fs2_bin")
        self.verticalLayout_2.addWidget(self.fs2_bin)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem1)
        self.tabs.addTab(self.fs2, "")
        self.mods = QtGui.QWidget()
        self.mods.setObjectName("mods")
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.mods)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label = QtGui.QLabel(self.mods)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.verticalLayout_3.addWidget(self.label)
        self.modTree = QtGui.QTreeWidget(self.mods)
        self.modTree.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.modTree.setProperty("showDropIndicator", False)
        self.modTree.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.modTree.setAnimated(True)
        self.modTree.setExpandsOnDoubleClick(False)
        self.modTree.setObjectName("modTree")
        self.verticalLayout_3.addWidget(self.modTree)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.update = QtGui.QPushButton(self.mods)
        self.update.setObjectName("update")
        self.horizontalLayout.addWidget(self.update)
        self.reset_sel = QtGui.QPushButton(self.mods)
        self.reset_sel.setObjectName("reset_sel")
        self.horizontalLayout.addWidget(self.reset_sel)
        self.apply_sel = QtGui.QPushButton(self.mods)
        self.apply_sel.setObjectName("apply_sel")
        self.horizontalLayout.addWidget(self.apply_sel)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.tabs.addTab(self.mods, "")
        self.settings = QtGui.QWidget()
        self.settings.setObjectName("settings")
        self.verticalLayout_5 = QtGui.QVBoxLayout(self.settings)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.label_2 = QtGui.QLabel(self.settings)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_5.addWidget(self.label_2)
        self.sourceList = QtGui.QListWidget(self.settings)
        self.sourceList.setDragEnabled(True)
        self.sourceList.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.sourceList.setObjectName("sourceList")
        self.verticalLayout_5.addWidget(self.sourceList)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.addSource = QtGui.QPushButton(self.settings)
        self.addSource.setObjectName("addSource")
        self.horizontalLayout_2.addWidget(self.addSource)
        self.editSource = QtGui.QPushButton(self.settings)
        self.editSource.setObjectName("editSource")
        self.horizontalLayout_2.addWidget(self.editSource)
        self.removeSource = QtGui.QPushButton(self.settings)
        self.removeSource.setObjectName("removeSource")
        self.horizontalLayout_2.addWidget(self.removeSource)
        self.verticalLayout_5.addLayout(self.horizontalLayout_2)
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.schemeHandler = QtGui.QPushButton(self.settings)
        self.schemeHandler.setObjectName("schemeHandler")
        self.gridLayout.addWidget(self.schemeHandler, 0, 0, 1, 1)
        self.verticalLayout_5.addLayout(self.gridLayout)
        self.tabs.addTab(self.settings, "")
        self.tab = QtGui.QWidget()
        self.tab.setObjectName("tab")
        self.verticalLayout_4 = QtGui.QVBoxLayout(self.tab)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.aboutLabel = QtGui.QLabel(self.tab)
        self.aboutLabel.setObjectName("aboutLabel")
        self.verticalLayout_4.addWidget(self.aboutLabel)
        self.tabs.addTab(self.tab, "")
        self.verticalLayout.addWidget(self.tabs)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 544, 19))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.tabs.setCurrentIndex(2)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "Mod Manager", None, QtGui.QApplication.UnicodeUTF8))
        self.gogextract.setText(QtGui.QApplication.translate("MainWindow", "Install FS2 with the GOG installer", None, QtGui.QApplication.UnicodeUTF8))
        self.select.setText(QtGui.QApplication.translate("MainWindow", "Select installed FS2 (Open)", None, QtGui.QApplication.UnicodeUTF8))
        self.fs2_bin.setText(QtGui.QApplication.translate("MainWindow", "Selected FS2: ...", None, QtGui.QApplication.UnicodeUTF8))
        self.tabs.setTabText(self.tabs.indexOf(self.fs2), QtGui.QApplication.translate("MainWindow", "FS2", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("MainWindow", "Select mods to install them or deselect them to uninstall them. Click on a mod\'s name to get more information about it.", None, QtGui.QApplication.UnicodeUTF8))
        self.modTree.setSortingEnabled(True)
        self.modTree.headerItem().setText(0, QtGui.QApplication.translate("MainWindow", "Name", None, QtGui.QApplication.UnicodeUTF8))
        self.modTree.headerItem().setText(1, QtGui.QApplication.translate("MainWindow", "Version", None, QtGui.QApplication.UnicodeUTF8))
        self.modTree.headerItem().setText(2, QtGui.QApplication.translate("MainWindow", "Status", None, QtGui.QApplication.UnicodeUTF8))
        self.update.setText(QtGui.QApplication.translate("MainWindow", "Update List", None, QtGui.QApplication.UnicodeUTF8))
        self.reset_sel.setText(QtGui.QApplication.translate("MainWindow", "Reset Selection", None, QtGui.QApplication.UnicodeUTF8))
        self.apply_sel.setText(QtGui.QApplication.translate("MainWindow", "Install/Uninstall", None, QtGui.QApplication.UnicodeUTF8))
        self.tabs.setTabText(self.tabs.indexOf(self.mods), QtGui.QApplication.translate("MainWindow", "Mods", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("MainWindow", "Mod Sources:", None, QtGui.QApplication.UnicodeUTF8))
        self.addSource.setText(QtGui.QApplication.translate("MainWindow", "Add", None, QtGui.QApplication.UnicodeUTF8))
        self.editSource.setText(QtGui.QApplication.translate("MainWindow", "Edit", None, QtGui.QApplication.UnicodeUTF8))
        self.removeSource.setText(QtGui.QApplication.translate("MainWindow", "Remove", None, QtGui.QApplication.UnicodeUTF8))
        self.schemeHandler.setText(QtGui.QApplication.translate("MainWindow", "Install as handler for fs2:// links", None, QtGui.QApplication.UnicodeUTF8))
        self.tabs.setTabText(self.tabs.indexOf(self.settings), QtGui.QApplication.translate("MainWindow", "Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.aboutLabel.setText(QtGui.QApplication.translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Idea and implementation in Bash by Hellzed.</p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Port to Python by ngld.</p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">For feedback and updates go to:<br /><a href=\"http://www.hard-light.net/forums/index.php?topic=86364\"><span style=\" text-decoration: underline; color:#0000ff;\">http://www.hard-light.net/forums/index.php?topic=86364</span></a> (for now)</p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">The code is available at:<br /><a href=\"https://github.com/ngld/fs2mod-py\"><span style=\" text-decoration: underline; color:#0000ff;\">https://github.com/ngld/fs2mod-py</span></a><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Dependencies:</p>\n"
"<ul style=\"margin-top: 0px; margin-bottom: 0px; margin-left: 0px; margin-right: 0px; -qt-list-indent: 1;\"><li style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><a href=\"http://python.org\"><span style=\" text-decoration: underline; color:#0000ff;\">Python</span></a> (2 or 3)</li>\n"
"<li style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><a href=\"http://qt-project.org/wiki/Category:LanguageBindings::PySide\"><span style=\" text-decoration: underline; color:#0000ff;\">PySide</span></a> or <a href=\"http://riverbankcomputing.co.uk/software/pyqt/intro\"><span style=\" text-decoration: underline; color:#0000ff;\">PyQt4</span></a></li>\n"
"<li style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><a href=\"http://www.7-zip.org/\"><span style=\" text-decoration: underline; color:#0000ff;\">7zip</span></a> (to extract downloaded archives)</li></ul>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">This tool also uses <a href=\"http://constexpr.org/innoextract/\"><span style=\" text-decoration: underline; color:#0000ff;\">InnoExtract</span></a> to unpack the GOG installer.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.tabs.setTabText(self.tabs.indexOf(self.tab), QtGui.QApplication.translate("MainWindow", "About", None, QtGui.QApplication.UnicodeUTF8))

