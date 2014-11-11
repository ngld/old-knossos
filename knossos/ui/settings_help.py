# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings_help.ui'
#
# Created: Tue Nov 11 21:40:38 2014
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
        self.label = QtGui.QLabel(Form)
        self.label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label.setWordWrap(True)
        self.label.setOpenExternalLinks(True)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Form", "<html><head/><body><p>If you need help, you can either check <a href=\"http://www.hard-light.net/forums/index.php?topic=86364.msg1768735#msg1768735\"><span style=\" text-decoration: underline; color:#0000ff;\">this release post</span></a> or <a href=\"https://github.com/ngld/knossos/issues\"><span style=\" text-decoration: underline; color:#0000ff;\">check the reported issues</span></a>.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))

