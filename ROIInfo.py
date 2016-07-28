'''
Created on Mar 3, 2015
  execute   "pyuic4 ROIInfoGui.ui -o ROIInfoGui.py" from system shell to regenerate ROIViewGui.py from ROIViewGui.ui
@author: stephen russek
'''
from PyQt4 import QtGui, QtCore
from ROIInfoGui import Ui_ROIInfoWindow

class ROIInfoWindow(QtGui.QMainWindow):
    def __init__(self ,  parent = None):
        super(ROIInfoWindow, self).__init__()
        self.ui = Ui_ROIInfoWindow()
        self.ui.setupUi(self)
        self.setWindowTitle('ROI Info')
        self.ui.pbUpdate.clicked.connect(self.saveChanges)
        
    def update(self,roiset, roi, roiview):
      self.roi=roi
      self.roiview=roiview
      self.ui.lblROISet.setText(roiset.ROIName)
      self.ui.lblROIType.setText(roi.Type)
      self.ui.lblROIIndex.setText(str(roi.Index))
      self.ui.txtXCenter.setText("{:.2f}".format(roi.Xcenter))
      self.ui.txtYCenter.setText("{:.2f}".format(roi.Ycenter))
      self.ui.txtZCenter.setText("{:.2f}".format(roi.Zcenter))
      self.ui.txtd1.setText("{:.2f}".format(roi.d1))  
      self.ui.txtT1.setText("{:.2f}".format(roi.T1))
      self.ui.txtT2.setText("{:.2f}".format(roi.T2))
      self.ui.txtADC.setText("{:.2f}".format(roi.ADC*1000))
      self.ui.txtConcentration.setText("{:.2f}".format(roi.Concentration))
      self.ui.txtProtonDensity.setText("{:.2f}".format(roi.PD))
      self.ui.lblAve.setText("{:.3f}".format(roi.SignalAve))
      self.ui.lblSd.setText("{:.3f}".format(roi.SignalRMS))
      
    def saveChanges(self):
      roi=self.roi
      try:
        roi.Xcenter=float(self.ui.txtXCenter.toPlainText())
        roi.Ycenter=float(self.ui.txtYCenter.toPlainText())
        roi.Zcenter=float(self.ui.txtZCenter.toPlainText())
        roi.d1=float(self.ui.txtd1.toPlainText())  
        roi.T1=float(self.ui.txtT1.toPlainText())
        roi.T2=float(self.ui.txtT2.toPlainText())
        roi.ADC=float(self.ui.txtADC.toPlainText())/1000
        roi.Concentration=float(self.ui.txtConcentration.toPlainText())
        roi.PD=float(self.ui.txtProtonDensity.toPlainText())
      except:
        pass

      self.roiview.redrawROIs()
   

 
