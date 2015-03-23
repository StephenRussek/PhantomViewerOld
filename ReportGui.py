# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ReportGui.ui'
#
# Created: Wed Jan 28 15:27:30 2015
#      by: PyQt4 UI code generator 4.9.6
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Report(object):
    def setupUi(self, Report):
        Report.setObjectName(_fromUtf8("Report"))
        Report.resize(1148, 937)
        self.centralwidget = QtGui.QWidget(Report)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.txtReport = QtGui.QTextEdit(self.centralwidget)
        self.txtReport.setGeometry(QtCore.QRect(10, 10, 1121, 866))
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("Consolas"))
        font.setPointSize(8)
        font.setKerning(False)
        self.txtReport.setFont(font)
        self.txtReport.setFrameShape(QtGui.QFrame.WinPanel)
        self.txtReport.setDocumentTitle(_fromUtf8(""))
        self.txtReport.setObjectName(_fromUtf8("txtReport"))
        Report.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(Report)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1148, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setObjectName(_fromUtf8("menuFile"))
        Report.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(Report)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        Report.setStatusBar(self.statusbar)
        self.actionSave = QtGui.QAction(Report)
        self.actionSave.setObjectName(_fromUtf8("actionSave"))
        self.actionClear_Report = QtGui.QAction(Report)
        self.actionClear_Report.setObjectName(_fromUtf8("actionClear_Report"))
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionClear_Report)
        self.menubar.addAction(self.menuFile.menuAction())

        self.retranslateUi(Report)
        QtCore.QMetaObject.connectSlotsByName(Report)

    def retranslateUi(self, Report):
        Report.setWindowTitle(_translate("Report", "ROI Analysis Report", None))
        self.menuFile.setTitle(_translate("Report", "File", None))
        self.actionSave.setText(_translate("Report", "Save", None))
        self.actionClear_Report.setText(_translate("Report", "Clear Report", None))

