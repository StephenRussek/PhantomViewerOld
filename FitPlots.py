'''
Created on Dec 30, 2014
Uses FitPlotsGui.py created from FitPlots.ui by QT4
  execute   "pyuic4 FitPlotsGui.ui -o FitPlotsGui.py" 
@author: stephen russek
'''
from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
import pyqtgraph.opengl as gl
import pyqtgraph.functions as fn
from FitPlotsGui import Ui_FitPlotsGui

class FitPlots(QtGui.QMainWindow):
    def __init__(self , x, y, fx, fy, parent = None):
        super(FitPlots, self).__init__()
        self.ui = Ui_FitPlotsGui()
        self.ui.setupUi(self)
        self.setWindowTitle('Fits')
        self.fitPlot=self.ui.gvFitPlot
        self.ui.vsROI.setMaximum(y.shape[0])  #set vertical slider maximum to number of curves
        self.ui.vsROI.valueChanged.connect(self.plotROIdata) 
        self.x=x
        self.y=y
        self.fx=fx
        self.fy=fy
        self.fitPlot.plot(self.x, self.y[0,:], pen=None,  symbolPen=None, symbolSize=20, symbolBrush=(255, 0, 0)) 
        self.fitPlot.plot(self.fx, self.fy[0,:],pen={'color': (255,0,0), 'width': 3}, symbol =None)

    def plotROIdata(self):
      nROI=self.ui.vsROI.value()-1
      self.ui.gvFitPlot.clear()
      self.fitPlot.plot(self.x, self.y[nROI,:], pen=None,  symbolPen=None, symbolSize=20, symbolBrush=(255, 0, 0))
      self.fitPlot.plot(self.fx, self.fy[nROI,:],pen={'color': (255,0,0), 'width': 3}, symbol =None)
      
   