'''
Created on Dec 29, 2014
Uses ReportGui.py created from Report.ui by QT4
  execute   "pyuic4 ReportGui.ui -o ReportGui.py" 
@author: stephen russek
'''
from PyQt4 import QtGui, QtCore
from ReportGui import Ui_Report

class Report(QtGui.QMainWindow):
    def __init__(self ,parent = None):
        super(Report, self).__init__()
        self.ui = Ui_Report()
        self.ui.setupUi(self)
        self.setWindowTitle('Report')
        self.ui.actionSave.triggered.connect(self.writeFile)


    def printReport(self, string):
      self.ui.txtReport.clear()
      self.ui.txtReport.insertPlainText(string)
      
    def writeFile (self):
      fileName = QtGui.QFileDialog.getSaveFileName(parent=None, caption="Report File Name", directory = '', selectedFilter = ".txt")
      if not fileName:  #if cancel is pressed return
        return None
      f= open(fileName, 'w')
      f.write(self.ui.txtReport.toPlainText())
      f.close()
      
 