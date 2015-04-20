# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 16:30:54 2013
Class to display and analyze phantom data
modules required pydicom : pip install pydicom --upgrade
Uses ROIViewGui created from ROIViewGui.ui by QT4
  execute   "pyuic4 ROIViewGui.ui -o ROIViewGui.py" from system shell to regenerate ROIViewGui.py from ROIViewGui.ui
@author: Stephen Russek
Units: times in ms, distances in mm, ADC in mm2/s, Temperature in C, 
last modification: 2-21-15
"""
import sys
import os     #operating system file/directory names
import copy   #copies objects eg ROIsets     
from PyQt4 import QtGui, QtCore
from ROIViewGui import Ui_ROIViewGui
import ROIProperties, ROIInfo, PhantomProperties
import DICOMDIRlist
import VPhantom, SystemPhantom, DiffusionPhantom,NISThcpPhantom, NISTKTPhantom, NISThcpCoronalPhantom
import numpy as np
import numpy.ma as ma   #masked arrays eg ROI arrays
import dicom    #import pydicom to read data sets and DICOMDIR
import pyqtgraph as pg
import pyqtgraph.opengl as gl
import pyqtgraph.functions as fn
import time # use for time, date and sleep
import lmfit  #used for nonlinear least square fits,builds on Levenberg-Marquardt algorithm of scipy.optimize.leastsq(),
import T1IRabs, T1VFA, T1VTR, T2SE, DifModel # models for data fitting
import Report, Info
import FitPlots   #Plot window to compare data to fits
import ImageList  #class to make an image list from a stack of image files
try:
    from unwrap import unwrap   #package for phase unwrapping
except:
  pass

class ROIView(QtGui.QMainWindow):
  """Main ROI viewing window, customized for different analysis eg geometric distortion, T1, T2, SNR etc"""
  def __init__(self, dt,parent = None):
    super(ROIView, self).__init__()
    pg.setConfigOption('background', 0.2)   #Background on plots 0 = black, 1 = white
    pg.setConfigOption('foreground', 'w')
    self.ui = Ui_ROIViewGui()
    self.ui.setupUi(self)
    self.modDate = '2/1/2015'
    self.wTitle = "PhantomViewer: " 
    self.setWindowTitle(self.wTitle)
    self.nImages=0
    self.nCurrentImage=0
    self.ims=imageStackWindow(self)   #define separate window object  for the image stack
    self.imswin=self.ims.win      #image stack window
    self.imv = self.ims.imv    #image stack pyqtgraph image view object
 #   self.ui.gvDicomViewer=pg.ImageView(self.ui.gvDicomViewer,view = pg.PlotItem())  #main image view window
 #   self.imv=self.ui.gvDicomViewer

    try:
      self.imv.ui.normBtn.hide()    #new pyqtgraph does not have this button
    except:
      pass
    self.imv.ui.roiBtn.setText("Line scan")
    self.imv.ui.histogram.plot.setLogMode(None,True)    #set the histogram y axis to a log scale    
    self.imv.vLine = pg.InfiniteLine(angle=90, movable=False)   #cross hair
    self.imv.hLine = pg.InfiniteLine(angle=0, movable=False)
    self.imv.addItem(self.imv.vLine, ignoreBounds=True)
    self.imv.addItem(self.imv.hLine, ignoreBounds=True)
    self.proxy = pg.SignalProxy(self.imv.view.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
    self.proxy2 = pg.SignalProxy(self.imv.view.scene().sigMouseClicked, rateLimit=60, slot=self.mouseClicked)
    self.rdPlot=self.ui.gvRawData   #plot widget for raw data
    self.resultsPlot=self.ui.gvResults  #plot widget for results of data fitting
    self.dicomHeader = "DICOM Header"
    self.setWindowTitle('ROI Viewer')
    self.ui.lblnImages.setText((str(self.nImages)))
    self.ui.lblCurrentImage.setText("none")
    self.ds= ImageList.ImageList()                         #list of data sets, can be dicom, tiff, fdf
    self.seriesFileNames = []
    self.image3D = np.array ([1,1]) 
#signals and slots
# Menu items
    self.ui.actionSelectImages.triggered.connect(self.openFile)
    #self.imwinOpenImages.addAction(self.openFile)    
    self.ui.actionClear_All_Images.triggered.connect(self.clearImages)
    self.ui.actionDelete_Current_Image.triggered.connect(self.deleteCurrentImage)
    
    self.ui.actionOpenPhantomFile.triggered.connect(self.openPhantomFile)
    self.ui.actionSystem_Phantom.triggered.connect(self.SystemPhantom)
    self.ui.actionDiffusion_Phantom.triggered.connect(self.DiffusionPhantom)
    self.ui.actionBreast_Phantom.triggered.connect(self.BreastPhantom)
    self.ui.actionNIST_hcp_Phantom.triggered.connect(self.NISThcpPhantom)
    self.ui.actionNIST_hcp_Coronal_Phantom.triggered.connect(self.NISThcpCoronalPhantom)
    self.ui.actionNIST_KT_Phantom.triggered.connect(self.NISTKTPhantom)
    self.ui.actionShowPhantomInfo.triggered.connect(self.showPhantomProperties)
    self.ui.actionSave_phantom_file.triggered.connect(self.savePhantomFile) 
       
    self.ui.actionOpen_ROI_File.triggered.connect(self.openROIFile)    
    self.ui.actionShow_ROI_Properties.triggered.connect(self.showROIInfo)
    self.ui.actionShowHide_ROIs.triggered.connect(self.toggleShowROIs)
    self.ui.actionReset_ROIs.triggered.connect(self.resetROIs) 

    self.ui.actionT1_Analysis.triggered.connect(self.T1Analysis)
    self.ui.actionT2_Analysis.triggered.connect(self.T2Analysis)
    self.ui.actionProton_density_SNR.triggered.connect(self.PDSNRAnalysis)
    self.ui.actionDiffusion.triggered.connect(self.diffusionAnalysis)
    self.ui.action3dViewer.triggered.connect(self.View3d)
    self.ui.actionView3D_color.triggered.connect(self.view3DColor)
    self.ui.actionView3D_transparency.triggered.connect(self.view3DTransparency)
    self.ui.actionWrite_to_DICOM.triggered.connect(self.writeDicomFiles)
    self.ui.actionFitting_Results.triggered.connect(self.outputReport)
    self.ui.actionSave_Results.triggered.connect(self.saveReport)
    self.ui.actionClear_Report.triggered.connect(self.clearReport)
    self.ui.txtDicomHeader.setHidden(False)
    self.ui.txtResults.setHidden(False)
    self.ui.actionPhase_Unwrap.triggered.connect(self.unWrapCurrentImage)
    self.ui.actionPlane_Background_Subtract.triggered.connect(self.planeBackgroundSubtract)
    self.ui.actionParabola_Background_Subtract.triggered.connect(self.ParabolaBackgroundSubtract)
    self.ui.actionROI_Color.triggered.connect(self.ROIColor)
#  push buttons and sliders
    self.ui.hsROISet.valueChanged.connect(self.changeROISet)
    self.ui.vsImage.valueChanged.connect(self.imageSlider)
    self.ui.pbReflectX.clicked.connect(self.reflectX)
    self.ui.pbReflectY.clicked.connect(self.reflectY)
    self.ui.pbReflectZ.clicked.connect(self.reflectZ)
    self.ui.pbShowRawData.clicked.connect(self.showRawData)
    self.ui.pbFitData.clicked.connect(self.fitData) 
    self.ui.pbViewFits.clicked.connect(self.viewFits)     
    self.ui.hsAngle.valueChanged.connect(self.rotateROIs) 
    self.ui.hsSize.valueChanged.connect(self.reSizeROIs)
    self.ui.rbEditROIset.clicked.connect(self.editROISet)
    self.ui.rbEditSingleROI.clicked.connect(self.editSingleROI)
    self.ui.rbAllSlices.clicked.connect(self.allSlices)
    self.ui.rbSelectedSlice.clicked.connect(self.currentSlice)
    self.ui.rbUseROIValues.clicked.connect(self.useROIValues)   #flag self.useROIValues = True  use nominal values as initial guess
    self.ui.rbUseBestGuess.clicked.connect(self.useBestGuess)    #flag self.useROIValues = False 
    self.ui.rbViewDicomHeader.toggled.connect(self.viewDicomHeader)
    self.ui.txtDicomHeader.setHidden(True)  #Image header normally hidden
    self.ui.chShowBackgroundROIs.clicked.connect(self.showROIs)
    #self.ui.rbViewMessages.toggled.connect(self.viewMessages)
#  setup regions of interest (ROIs)
    self.dataType = str(dt)    #string indicating data type "T1", "T2", "PD-SNR", DIF ; determines what fitting models are accessible
    self.setDataType(self.dataType)
    self.ADCmap = False
    self.Phantom = VPhantom.VPhantom()
    self.ui.lblPhantomType.setText(self.Phantom.phantomName)
    self.ROIset = "T1Array"   #determines which ROI set to use via ROIsetdict 
    self.InitialROIs = VPhantom.ROISet("default")     #Current ROIs are initial ROIs with global rotation and translation
    self.currentROIs=copy.deepcopy(self.InitialROIs)
    self.currentROI = 1   #currently selected ROI
    self.useROIValues = False    #flag to instruct fits to take initial guesses from the current ROI values
    self.pgROIs=[]  #list of pyqtgraph ROIs
    self.pgROIlabels = []   #List of labels that go with ROIs
    self.bShowROIs = False    #Flag to determine if ROIs are shown or hidden
    self.roiPen = pg.mkPen('g', width=3) #one of: r, g, b, c, m, y, k, w    or R, G, B, [A]    integers 0-255  or (R, G, B, [A])  tuple of integers 0-255
    self.lblColor=(255,204,0)
    self.lblFont=QtGui.QFont()
    self.lblFont.setPixelSize(18)
    self.bShowSNRROIs = False    #flag to show SNR ROIs to measure background signal; used to determine points that are in the background
    self.bSNRROIs  = False      #flag to indicate SNR ROIs are plotted
    self.snrPen = pg.mkPen('y', width=3)
    self.ROItrans=np.array([0,0,0], float)  #ROI translation
    self.bResetROIs = True  #flag to reset ROIs to initials positions
    self.relativeOffseth = 0.0  #horizontal and vertical offsets of the ROI positions
    self.relativeOffsetv = 0.0
    self.theta = 0.0                 #current rotation of the ROIs in radians
    self.bEditROISet = True   #flag to specify whether to edit ROI set or an individual ROI
    self.bAllSlices = False   #flag to specify if all slices will be analyzed or just currently selected one
    self.view3DColor = QtGui.QColor(255, 255 ,255 , alpha=10)
    self.view3DBackground = QtGui.QColor(155, 155 ,255 , alpha=10)
    self.view3DTransparency = 1.75   #set transparency scaling for 3dview, 1 = transparency set by voxel value

#global data structures
    self.rdy = np.array([0.,0.]) # 2d numpy array of raw data (usually signal averaged i= ROI j=image number in stack)
    self.rdx = np.array([0.]) # numpy array of imaging parameter that is varied ie TE, TI, FA etc; usually a 1d array (independent variable)
    self.rdBackground = np.array([0.])   #average background counts in signal free region in reduced image array
    self.background = 0.    #background averaged over images
    self.noisefactor= 1.5   #data below noisefactor*background will not be fit
    self.fity=np.zeros((14,100)) # 2d numpy array of fitting model using optimized parameters
    self.fitx = np.arange(100) # 100 element numpy array of imaging parameter spanning range of image data (independent variable)
    self.clickArray = []   # list of numpy array of points generated from mouse clicks on the images
    self.T1Params = []  #list of lmfit dictionaries
    self.report=""      # String to record all output to allow printing or saving a report
    self.imageDirectory = '' #last opened image directory
    self.showReferenceValues = True   #flag to show reference parameter values listed in phantom type or ROI file
    self.sliceList = []    #ordered list of slices in the current image stack

  def setupPhantom(self, phantom):
    self.Phantom=phantom
    self.ui.lblPhantomType.setText(self.Phantom.phantomName)
    self.currentROIs = self.Phantom.ROIsets[0]     #Current ROIs are initial ROIs with global rotation and translation
    self.ui.hsROISet.setMaximum(len(self.Phantom.ROIsets)-1)
    self.ui.hsROISet.setValue(0)
    self.ui.lblROISet.setText(self.Phantom.ROIsets[0].ROIName)
    self.ROIset = self.Phantom.ROIsets[0].ROIName   #determines which ROI set to use via ROIsetdict   
    self.InitialROIs=copy.deepcopy(self.currentROIs)    #make copy to reset if necessary
    self.roiPen = pg.mkPen(self.currentROIs.ROIColor, width=3)
    self.useROIValues = False   #default use best guess for initial fitting parameters, if true use ROI values
    self.ui.rbUseBestGuess.setChecked(True)   #does not seem to work
    self.showReferenceValues = True
    self.resetROIs()
 
  def SystemPhantom (self):
    self.setupPhantom(SystemPhantom.SystemPhantom())
   
  def DiffusionPhantom (self):
    self.setupPhantom(DiffusionPhantom.DiffusionPhantom())
    self.dataType = "Dif"
    self.setDataType(self.dataType)

  def BreastPhantom (self):
    pass
  
  def NISThcpPhantom (self):
    self.setupPhantom(NISThcpPhantom.hcpPhantom())
      
  def NISThcpCoronalPhantom (self):
    self.setupPhantom(NISThcpCoronalPhantom.hcpCoronalPhantom())
        
  def NISTKTPhantom (self):
    self.setupPhantom(NISTKTPhantom.KTPhantom())
    
  def showPhantomInfo(self):
    '''Shows phantom information and image'''
    if hasattr(self,"InfoWindow")==False:
        self.InfoWindow = Info.InfoWindow()
    self.InfoWindow.show()
    self.InfoWindow.setWindowTitle(self.Phantom.phantomName )
    self.InfoWindow.ui.lblInfo.setPixmap(QtGui.QPixmap('MRISystemPhantom.jpg'))
    self.InfoWindow.ui.lblInfo.show()
        
  def showPhantomProperties(self):
    '''Shows phantom image'''
    if hasattr(self,"PhantomProperties")==False:
        self.PhantomProperties = PhantomProperties.PhantomProperties(self.Phantom)
    self.PhantomProperties.show()
    self.PhantomProperties.setWindowTitle(self.Phantom.phantomName )
               
  def openDICOMdir (self,filename):
    """Opens DICOMDIR and selected image series"""
    d1= []  #d1 is 3d data stack for 3d images
    dcmdir = dicom.read_dicomdir(str(filename))
    if hasattr(self,"DICOMDIRGui")==False:
      self.DICOMDIRlist=DICOMDIRlist.DICOMDIRlist(self)
      self.DICOMDIRlist.setWindowTitle("DICOMDIR list" )
    self.DICOMDIRlist.ui.lblDICOMDIR.setText(filename)
    dv=self.DICOMDIRlist.ui.listDICOMDIR
    for patrec in dcmdir.patient_records:
      s = "Patient: {0.PatientID}: {0.PatientsName}".format(patrec)
      studies = patrec.children
      for study in studies:
            s= s + "    Study {0.StudyID}: {0.StudyDate}".format(study)
            try:
              s= s + "    Study description {0.StudyDescription}".format(study)
            except:
                pass
            dv.addItem(s)
            all_series = study.children
            for series in all_series:
                nImages = len(series.children)
                plural = ('', 's')[nImages > 1]
                if not 'SeriesDescription' in series:
                    series.SeriesDescription = "N/A"
                s= "Series={0.SeriesNumber},  {0.Modality}: {0.SeriesDescription}"  " ({1} image{2})".format(series, nImages, plural)
                dv.addItem(s)
                image_records = series.children
                image_filenames = [os.path.join(self.imageDirectory, *image_rec.ReferencedFileID) for image_rec in image_records]
      if self.DICOMDIRlist.exec_():   #dialog to return list of selected DICOM series to open
        nSeries=self.DICOMDIRlist.selectedSeries()
      else:
        return
      nImages = 0
      for study in studies:
          all_series = study.children
          for series in all_series:
            if str(series.SeriesNumber) in nSeries:
              nImages += len(series.children)
              image_records = series.children
              image_filenames = [os.path.join(self.imageDirectory, *image_rec.ReferencedFileID) for image_rec in image_records]
              self.seriesFileNames.extend(image_filenames)
              nFiles= len(image_filenames)
              dialogBox = QtGui.QProgressDialog(labelText = 'Importing Files...',minimum = 0, maximum = nFiles)
              dialogBox.setCancelButton(None)
              dsets= [dicom.read_file(image_filename)for image_filename in image_filenames]
              for i,dcds in enumerate(dsets):   #unpack DICOM data sets (dcds)
                self.ds.unpackImageFile (dcds, image_filenames[i], "dcm")
                d1.append(self.ds.PA[i+1])
                dialogBox.setValue(i)
    self.nImages += nImages
    self.ui.lblnImages.setText(str(self.nImages))
    self.ui.vsImage.setMinimum(1)       #set slider to go from 1 to the number of images
    self.ui.vsImage.setMaximum(self.nImages)
    self.nCurrentImage=1
    self.ui.vsImage.setValue(self.nCurrentImage)
    self.displayCurrentImage()
    self.image3D= np.dstack(d1)
    self.imswin.show()
                                             
  def openFile (self):
    d1= []  #d1 is 3d data stack for 3d images
    self.fileNames = QtGui.QFileDialog.getOpenFileNames(self,"Open Image Files  or DICOMDIR",self.imageDirectory ) 
    if not self.fileNames:  #if cancel is pressed return
      return None
    self.imageDirectory=os.path.dirname(str(self.fileNames[0]))#Save current directory   
    if len(self.fileNames) == 1:    #check to see if file is a DICOMDIR
      filename=self.fileNames[0]
      if "DICOMDIR" in filename: 
          self.openDICOMdir(filename)
          return None                                            
    self.seriesFileNames.extend(self.fileNames)     #concatenate new file list with previous file list
    nFiles= len(self.fileNames)
    dialogBox = QtGui.QProgressDialog(labelText = 'Importing Files...',minimum = 0, maximum = nFiles)
    dialogBox.setCancelButton(None)
    for i in range(nFiles):
      fileName = self.fileNames[i]
      fstatus=self.ds.addFile(fileName)
      if fstatus[0]:
        d1.append(self.ds.PA[i+1])
        dialogBox.setValue(i)
      else:
        self.msgPrint(fstatus[1])   #Could not open or read file
    self.sliceList = sorted(set(self.ds.SliceLocation))   #make an ordered list of slices
    self.nImages=self.nImages+len(self.ds.FileName)-1
    self.ui.lblnImages.setText(str(self.nImages))
    if self.nImages < 1 :
      limage = 0
    else:
      limage = 1
    self.ui.vsImage.setMinimum(limage)       #set slider to go from 1 to the number of images
    self.ui.vsImage.setMaximum(self.nImages)
    self.nCurrentImage=limage
    self.ui.vsImage.setValue(self.nCurrentImage)
    self.displayCurrentImage()
    if len(d1)>0:
      self.image3D= np.dstack(d1)
    self.imswin.show()

  def writeDicomFiles (self):
    fileName = QtGui.QFileDialog.getSaveFileName(parent=None, caption="Dicom File Name")
    if not fileName:  #if cancel is pressed return
      return None
    self.ds.writeDicomFiles(fileName)   #write current image list in DICOM format to filename+ imagenumber + .dcm
         
  def changeROISet (self):
    self.InitialROIs =self.Phantom.ROIsets[self.ui.hsROISet.value()]
    self.ui.lblROISet.setText(self.InitialROIs.ROIName)
    self.resetROIs()
      
  def imageSlider (self):
    self.nCurrentImage=self.ui.vsImage.value()
    self.displayCurrentImage()
      
  def displayCurrentImage (self):
    '''Displays current image as set by self.nCurrentImage and associated header parameters'''
    i=self.nCurrentImage
    self.ui.lblCurrentImage.setText(str(self.nCurrentImage)) 
    self.ui.lblDate.setText(format(self.ds.StudyDate[i])) 
    self.ui.lblDataType.setText(format(self.ds.DataType[i])) 
    self.ui.lblFileName.setText(self.ds.FileName[i]) 
    self.ui.lblManufacturer.setText(self.ds.Manufacturer[i]) 
    self.ui.lblSeries.setText(self.ds.SeriesDescription[i]) 
    self.ui.lblInstitution.setText(self.ds.InstitutionName[i]) 
    self.ui.lblField.setText(str(self.ds.MagneticFieldStrength[i]))
    self.ui.lblReceiveCoil.setText(str(self.ds.ReceiveCoilName[i]))    
    self.ui.lblPatient.setText(self.ds.PatientName[i]) 
    self.ui.lblProtocol.setText(str(self.ds.ProtocolName[i])) 
    self.ui.lblBW.setText(str(self.ds.PixelBandwidth[i])) 
    self.TEvaries=not(self.checkEqual(self.ds.TE))
    if self.TEvaries:
      self.T2Analysis()
    self.ui.lblTE.setStyleSheet("background-color: yellow") if self.TEvaries else self.ui.lblTE.setStyleSheet("background-color: white")  
    self.ui.lblTE.setText(str(self.ds.TE[i]))
    self.TRvaries = not(self.checkEqual(self.ds.TR))
    if self.TRvaries:
      self.ui.tabT1.setCurrentIndex(2)
    self.ui.lblTR.setStyleSheet("background-color: yellow") if self.TRvaries else self.ui.lblTR.setStyleSheet("background-color: white")
    self.ui.lblTR.setText(str(self.ds.TR[i])) 
    self.ui.lblColumns.setText(str(self.ds.Columns[i]))  
    self.ui.lblRows.setText(str(self.ds.Rows[i]))
    self.TIvaries = not(self.checkEqual(self.ds.TI))
    if self.TIvaries:
      self.ui.tabT1.setCurrentIndex(0)
    self.ui.lblTI.setStyleSheet("background-color: yellow") if self.TIvaries else self.ui.lblTI.setStyleSheet("background-color: white")    
    self.ui.lblTI.setText(str(self.ds.TI[i])) 
    self.ui.lblSliceThickness.setText("{:.2f}".format(self.ds.SliceThickness[i]))
    self.sliceLocationVaries = not(self.checkEqual(self.ds.SliceLocation))
    self.ui.lblSliceLocation.setStyleSheet("background-color: yellow") if self.sliceLocationVaries else self.ui.lblSliceLocation.setStyleSheet("background-color: white")
    self.ui.lblSliceLocation.setText("{:.2f}".format(self.ds.SliceLocation[i])) 
    self.ui.lblPixelSpacingRow.setText("{:.2f}".format(self.ds.PixelSpacingX[i])) 
    self.ui.lblPixelSpacingCol.setText("{:.2f}".format(self.ds.PixelSpacingY[i]))
    self.FAvaries =  not(self.checkEqual(self.ds.FA))
    if self.FAvaries:
      self.ui.tabT1.setCurrentIndex(1)
    self.ui.lblFA.setStyleSheet("background-color: yellow") if self.FAvaries else self.ui.lblFA.setStyleSheet("background-color: white")    
    self.ui.lblFA.setText(str(self.ds.FA[i]))
    self.ui.lblPhaseEncodeDirection.setText(str(self.ds.InPlanePhaseEncodingDirection[i])) 
    self.ui.lblFoVX.setText(str(self.ds.FoVX[i]))
    self.ui.lblFoVY.setText(str(self.ds.FoVY[i]))    
    self.ui.lblbValue.setText(str(self.ds.bValue[i]))
    self.bvaries=not(self.checkEqual(self.ds.bValue))
    if self.bvaries:
      self.diffusionAnalysis()
      self.ui.lblbValue.setStyleSheet("background-color: yellow")
    else:
      self.ui.lblFA.setStyleSheet("background-color: white")    
    data = self.ds.PA[i]  
    xscale =self.ds.PixelSpacingX[i] if (self.ds.PixelSpacingX[i] > 0.) else 1
    yscale = self.ds.PixelSpacingY[i] if (self.ds.PixelSpacingY[i] > 0.) else 1
    xmin = -self.ds.FoVX[i]/2   #set origin to center of image, need to upgrade to set by DICOM tag
    ymin = -self.ds.FoVY[i]/2    
    self.ui.lblUpperLeft.setText("UL=" + "{:.1f}".format(self.ds.ImagePosition[i][0]) + "," + "{:.1f}".format(self.ds.ImagePosition[i][1]) + "," + "{:.1f}".format(self.ds.ImagePosition[i][2]))
    self.imv.setImage(data,pos = (xmin,ymin), scale = (xscale,yscale),)
    self.ui.txtDicomHeader.setText(self.ds.header[i])
#    self.ui.lbldX.setText(str(self.ROItrans[0]))
#    self.ui.lbldY.setText(str(self.ROItrans[1]))
#    self.ui.lbldZ.setText(str(self.ROItrans[2]))
    self.imv.getView().setLabel('bottom',self.DirectionLabel(self.ds.RowDirection[i]),"mm")
    self.imv.getView().setLabel('left',self.DirectionLabel(self.ds.ColumnDirection[i]),"mm")
    self.ui.lblScaleSlope.setText("{:.3e}".format(self.ds.ScaleSlope[i]))
    self.ui.lblScaleIntercept.setText("{:.3e}".format(self.ds.ScaleIntercept[i]))                               
         
  def toggleShowROIs(self):
      self.bShowROIs =not self.bShowROIs
      self.showROIs()
      
  def showROIs(self):  
    """Displays ROIs if bShowROI is True, erase ROIs if false"""
    if self.bShowROIs :
        self.roiPen = pg.mkPen(self.currentROIs.ROIColor, width=3)
        self.ui.lbldh.setText(str(self.relativeOffseth))
        self.ui.lbldv.setText(str(self.relativeOffsetv))
        self.ui.lblCurrentROIs.setText(str(self.currentROIs.ROIName))
        self.ui.lblnROIs.setText(str(self.currentROIs.nROIs))        
        self.pgROIs = []
        self.bShowSNRROIs = self.ui.chShowBackgroundROIs.isChecked()
        for roi in self.currentROIs.ROIs:
            r=np.array([roi.Xcenter,roi.Ycenter,roi.Zcenter])
            imCoord=self.GlobaltoRel(r,self.nCurrentImage)
            pgroi=fCircleROI(self,[imCoord[0]-roi.d1/2, imCoord[1]-roi.d1/2], [roi.d1, roi.d1],str(roi.Index), pen=self.roiPen)  #needs work
            pgroi.Index=roi.Index
            self.pgROIs.append(pgroi)
        for roi in self.pgROIs:
            self.imv.getView().addItem(roi)
            self.imv.getView().addItem(roi.label)
        if hasattr(self.Phantom, "SNRROIs") and self.bShowSNRROIs:
            roi=self.Phantom.SNRROIs.ROIs[0]
            r=np.array([roi.Xcenter,roi.Ycenter,roi.Zcenter])
            imCoord=self.GlobaltoRel(r,self.nCurrentImage)
            snrroi=fCircleROI(self,[imCoord[0]-roi.d1/2, imCoord[1]-roi.d1/2], [roi.d1, roi.d1],"SNR", pen=self.snrPen)
            self.imv.getView().addItem(snrroi)
            self.snrROI=snrroi
            self.bSNRROIs=True
    else:   #remove all ROIs from the images
        if hasattr(self,"pgROIs"):
          for roi in self.pgROIs:
            self.imv.getView().removeItem(roi)
            self.imv.getView().removeItem(roi.label)
        if self.bSNRROIs:
          self.imv.getView().removeItem(self.snrROI)
          self.bSNRROIs=False    
        self.pgROIs = []
        self.ui.lblnROIs.setText("")
        self.ui.lblCurrentROIs.setText("")        

  def showROIInfo(self):
      if self.ui.cbViewROIInfo.isChecked():   
        if hasattr(self,"ROIInfo")==False:
            self.ROIInfo = ROIInfo.ROIInfoWindow()
            self.ROIInfo.setWindowTitle(" ROI Info")
            self.ROIInfo.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            point        = self.rect().topLeft()
            self.ROIInfo.move(point) #QtCore.QPoint(self.width(), 0))      
        self.ROIInfo.update(self.currentROIs,self.currentROI, self)
        self.ROIInfo.show()
        
  def editROISet(self): 
    self.bEditROISet = True
    
  def editSingleROI(self): 
    self.bEditROISet = False
    
  def allSlices(self): 
    self.bAllSlices = True
    
  def currentSlice(self): 
    self.bAllSlices = False
    
  def useROIValues(self): 
    self.useROIValues = True 
  
  def useBestGuess(self): 
    self.useROIValues = False
       
  def resetROIs(self):
        self.currentROIs=copy.deepcopy(self.InitialROIs)
        self.theta=0.0
        self.ui.lblPhantomAngle.setText("0")
        self.ui.hsAngle.setValue(0)
        self.relativeOffseth = 0.0  #horizontal and vertical offsets of the ROI positions
        self.relativeOffsetv = 0.0
        self.redrawROIs()
        
  def redrawROIs(self):
        self.bShowROIs = False    #erase and redraw initial ROIs
        self.showROIs()  
        self.bShowROIs = True
        self.showROIs()  
           
  def ROIColor(self):  
    col = QtGui.QColorDialog.getColor()
    self.roiPen = pg.mkPen(col, width=3)
    self.redrawROIs()   
         
  def openROIFile(self):
        if hasattr(self,"ROIprop")==False:
            self.ROIprop = ROIProperties.ROIProperties(self.Phantom)
            self.ROIprop.setWindowTitle("ROI Properties")      
        self.ROIprop.openROIFile(self.imageDirectory)
        self.bShowROIs=True       
        self.redrawROIs() 
        
  def reflectX(self):
    for roi in self.currentROIs.ROIs:
      roi.Xcenter=-roi.Xcenter
    self.redrawROIs()
    
  def reflectY(self):
    for roi in self.currentROIs.ROIs:
      roi.Ycenter=-roi.Ycenter
    self.redrawROIs()

  def reflectZ(self):
    for roi in self.currentROIs.ROIs:
      roi.Zcenter=-roi.Zcenter
    self.redrawROIs() 
    
  def translateROIs(self,tvector,snap, roiindex):
        self.relativeOffseth += tvector[0]
        self.relativeOffsetv += tvector[1]
        self.ui.lbldh.setText(str(self.relativeOffseth))
        self.ui.lbldv.setText(str(self.relativeOffsetv))
        r=self.reltoGlobal(tvector[0],tvector[1],self.nCurrentImage)
        if self.bEditROISet == True:  #translate ROI set
          for roi in self.pgROIs:
            roi.translate(tvector, snap=False, finish=False)
            roi.label.setPos(roi.pos())
          self.currentROIs.translate(r)  
        else:   #translate single ROI with roiindex
          roi = self.pgROIs[roiindex-1]
          roi.translate(tvector, snap=False, finish=False)
          roi.label.setPos(roi.pos())
          self.currentROIs.ROIs[roiindex-1].translate(r)
                
  def rotateROIs(self):
    if hasattr(self,"currentROIs"):
      t=float(self.ui.hsAngle.value())/2
      self.ui.lblPhantomAngle.setText("{:.1f}".format(t))
      thetanew=float(t * np.pi / 180.)
      dtheta=thetanew-self.theta
      perpAxis=np.cross(self.ds.RowDirection[self.nCurrentImage], self.ds.ColumnDirection[self.nCurrentImage])
      self.theta=thetanew
      self.currentROIs.rotate(perpAxis, dtheta)
      for i, roi in enumerate(self.pgROIs):   #change position of ROIs in pyqtgraph imageview object
            r=np.array([self.currentROIs.ROIs[i].Xcenter,self.currentROIs.ROIs[i].Ycenter,self.currentROIs.ROIs[i].Zcenter])
            (h,v) = self.GlobaltoRel(r,self.nCurrentImage)
            roi.setPos((h-self.currentROIs.ROIs[i].d1/2,v-self.currentROIs.ROIs[i].d1/2))
            roi.label.setPos(h-self.currentROIs.ROIs[i].d1/2,v-self.currentROIs.ROIs[i].d1/2)  
            
  def deleteROI(self,roi):
    if roi.Index >> 0:
      del self.currentROIs.ROIs[roi.Index-1]
      for i,roi in enumerate(self.currentROIs.ROIs):    #rename ROI indexes
        roi.Index=i+1
    self.currentROIs.nROIs = len(self.currentROIs.ROIs)
    self.bShowROIs = False
    self.showROIs()        
    self.bShowROIs = True
    self.showROIs() 
    
  def addROI(self,pos): 
    newROI = VPhantom.ROI()
    r=self.reltoGlobal(pos.x(),pos.y(),self.nCurrentImage)
    newROI.Xcenter=r[0]
    newROI.Ycenter=r[1]
    newROI.Zcenter=r[2]
    newROI.d1=10
    newROI.Index=len(self.currentROIs.ROIs) +1
    newROI.Name = "def-" + str(newROI.Index)
    self.currentROIs.ROIs.append(newROI)
    self.bShowROIs = False
    self.showROIs()        
    self.bShowROIs = True
    self.showROIs() 
    
  def reSizeROIs(self):
    if hasattr(self,"currentROIs"):
      size=float(self.ui.hsSize.value())/2
      self.ui.lblROISize.setText("{:.1f}".format(size))
      if self.bEditROISet == True:  #change size in ROI set
        for roi in self.currentROIs.ROIs: #initial ROIs remain unchanged
          roi.d1=size
      else:
        self.currentROI.d1=size
      for roi in self.pgROIs:   #erase ROIs
          self.imv.getView().removeItem(roi)
          self.imv.getView().removeItem(roi.label)  
      self.pgROIs = []
      self.showROIs()   #redraw ROIs 
                               
  def savePhantomFile(self):
      fileName = QtGui.QFileDialog.getSaveFileName(parent=None, caption="Save ROI File", directory = self.imageDirectory, selectedFilter = ".dat")
      if not fileName:  #if cancel is pressed return
        return None
      f= open(fileName, 'w')
      self.Phantom.ROIsets[0]=self.currentROIs
      s = self.Phantom.printROIinfo()
      f.write(s)
      f.close()
      
  def openPhantomFile(self):
      self.Phantom=VPhantom.VPhantom()
      self.Phantom.readPhantomFile(self.imageDirectory)
      self.InitialROIs =self.Phantom.ROIsets[0]
      self.ui.lblROISet.setText(self.InitialROIs.ROIName)
      self.ui.hsROISet.setMaximum(self.Phantom.nROISets)
      self.resetROIs()  
               
  def checkEqual(self, lst):    #returns True if all elements (except the 0th element) of the list are equal
    return lst[2:] == lst[1:-1]  

  def clearImages (self):  #Deletes all images except default image at index 1
    self.ds= ImageList.ImageList()                         #list of data sets, can be dicom, tiff, fdf
    del self.seriesFileNames[:]
    self.nCurrentImage=0
    self.nImages=0
    self.ui.txtResults.clear()
    #self.image3D.zeros [1,1,1]
    self.displayCurrentImage()
    self.ui.lblnImages.setText(str(self.nImages))
    self.ui.vsImage.setMaximum(0)   
    self.rdPlot.setLabel('left', "Counts", units='A')
    self.rdPlot.setLabel('bottom', "X Axis", units='s')
    self.rdPlot.setTitle("Raw Data")
    self.rdPlot.clear()
    self.resultsPlot.clear()
    self.resultsPlot.setLabel('bottom', "X Axis", units='s')
    self.resultsPlot.setTitle("Results")
#    self.resetROIs()

  def deleteCurrentImage(self):
    if self.nCurrentImage > 0:
      self.ds.deleteImage(self.nCurrentImage)
      self.nImages -= 1
      self.ui.lblnImages.setText(str(self.nImages))
      self.ui.vsImage.setMinimum(1)       #set slider to go from 1 to the number of images
      self.ui.vsImage.setMaximum(self.nImages)
      if self.nImages == 0:
          self.nCurrentImage=0
      else:
          self.nCurrentImage = 1
      self.ui.vsImage.setValue(self.nCurrentImage)
      self.displayCurrentImage()

  def unWrapCurrentImage(self):
    if self.nCurrentImage > 0:
      self.ds.PA[self.nCurrentImage] = unwrap(self.ds.PA[self.nCurrentImage],wrap_around_axis_0=False, wrap_around_axis_1=False,wrap_around_axis_2=False)
      self.displayCurrentImage() 

  def planeBackgroundSubtract(self):   
    r1=self.clickArray[-3]
    r2=self.clickArray[-2]
    r3=self.clickArray[-1]
    a=np.cross(r2-r1,r3-r1)
    an=np.linalg.norm(a)
    a=a/an
    plane=np.zeros([self.ds.Rows[self.nCurrentImage],self.ds.Columns[self.nCurrentImage]])
    for i in range(int(self.ds.Rows[self.nCurrentImage])):
        for j in range(int(self.ds.Columns[self.nCurrentImage])):
          plane[i,j]=(-a[0]*(i-r1[0])-a[1]*(j-r1[1]))/a[2]+r1[2]
    self.ds.PA[self.nCurrentImage]=self.ds.PA[self.nCurrentImage]-plane
    self.displayCurrentImage()  

  def ParabolaBackgroundSubtract(self):   
    r1=self.clickArray[-3]
    r2=self.clickArray[-2]
    r3=self.clickArray[-1]
    z1=self.clickArray[-3][2]
    z2=self.clickArray[-2][2]
    z3=self.clickArray[-1][2]
    r1[2]=0
    r2[2]=0
    r3[2]=0    
    Sav=(z1+z2)/2
    d=np.linalg.norm(np.cross((r2-r1),(r3-r1))/np.linalg.norm(r2-r1))
    a=(Sav-z3)/d**2
    print ("a= " + str(a))
    print ("Sav= " + str(Sav))
    print ("d= " + str(d))
    print ( str(z1) + str(z2)+str(z3))
#    self.PBGSubtract.setText("r1,r2,r3 = " +str(r1) + str(r2)+ str(r3))
#    self.PBGSubtract.setModal(True)
#    self.PBGSubtract.show()
    parab=np.zeros([self.ds.Rows[self.nCurrentImage],self.ds.Columns[self.nCurrentImage]])
    for i in range(int(self.ds.Rows[self.nCurrentImage])):
        for j in range(int(self.ds.Columns[self.nCurrentImage])):
          r0=np.array([i,j,0])
          d=np.linalg.norm(np.cross((r2-r1),(r0-r1))/np.linalg.norm(r2-r1))
          parab[i,j]=a*d**2
    self.ds.PA[self.nCurrentImage]=self.ds.PA[self.nCurrentImage]+parab
    self.displayCurrentImage()  
        
  def mouseClicked(self, evt):
    pos = evt[0]  ## using signal proxy turns original arguments into a tuple
    mousePoint = self.imv.view.vb.mapSceneToView(pos.scenePos())
    if abs(mousePoint.x()) < self.ds.FoVX[self.nCurrentImage]/2 and abs(mousePoint.y()) < self.ds.FoVY[self.nCurrentImage]/2:
      Xindex = int((mousePoint.x()+self.ds.FoVX[self.nCurrentImage]/2)/self.ds.PixelSpacingX[self.nCurrentImage]) #if self.ds.PixelSpacingX[self.nCurrentImage] > 0. else Xindex = int(mousePoint.x())
      Yindex = int((mousePoint.y()+self.ds.FoVY[self.nCurrentImage]/2)/self.ds.PixelSpacingY[self.nCurrentImage]) #if self.ds.PixelSpacingY[self.nCurrentImage] > 0. else Yindex = int(mousePoint.y())
      value=  self.ds.PA[self.nCurrentImage][Xindex,Yindex]      
      self.msgPrint ( "Add point: " +  "I= " + str(Xindex) + ", J=" + str(Yindex) + ", z=" + str(value) + "\n")
      pnt= np.array([float(Xindex),float(Yindex),float(value)])
      self.clickArray.append(pnt)
      if self.ui.rbDeleteROI.isChecked():
        self.deleteROI(self.currentROI)
      if self.ui.rbAddROI.isChecked():
        self.addROI(mousePoint)

  def viewDicomHeader (self):        
    if self.ui.rbViewDicomHeader.isChecked():
      self.ui.txtDicomHeader.setHidden(False)
      dh = str(self.ds.header[self.nCurrentImage])
      if dh == '':
          dh="DICOM Header"
      self.ui.txtDicomHeader.setText(dh)
    else:
      self.ui.txtDicomHeader.setHidden(True)
      
  #=============================================================================
  # def viewMessages (self):        
  #   if self.ui.rbViewMessages.isChecked():
  #     self.ui.txtResults.setHidden(False)
  #   else:
  #     self.ui.txtResults.setHidden(True)
  #=============================================================================
  def view3DColor(self):  
    self.view3DColor = QtGui.QColorDialog.getColor()
    self.View3d()
    
  def view3DTransparency(self):  
    t = 15.
    t , ok =  QtGui.QInputDialog.getInteger( None,'Transparency' , 'Enter value 1 (solid) to 100 transparent', value=15, min=1, max=100, step=1)
    if ok:
      self.view3DTransparency = t/10.0
      self.View3d() 
    
  def View3d(self):
      '''creates 3d rendering of current image stack'''
      if not hasattr(self,"view3Dwin"):   
        self.view3Dwin = gl.GLViewWidget()
        self.view3Dwin.opts['distance'] = 300
        self.view3Dwin.resize(800,800)
        self.view3Dwin.setWindowTitle('3D View ' )
      self.view3Dwin.show()
      try:
         self.view3Dwin.removeItem(self.image3DVol)
      except:
        pass
      ax = gl.GLAxisItem()
      self.view3Dwin.addItem(ax)
#       g = gl.GLGridItem()
#       g.scale(10, 10, 10)
#       self.view3Dwin.addItem(g) 
      data=self.image3D.astype(float) /float(self.image3D.max())  #normalize data to 1
      d2 = np.empty(data.shape + (4,), dtype=np.ubyte)
      d2[..., 0] = data * self.view3DColor.red()
      d2[..., 1] = data * self.view3DColor.green()
      d2[..., 2] = data * self.view3DColor.blue()
      d2[..., 3] = (data)**self.view3DTransparency * 255.   #sets transparency  
      d2[:, 0:3, 0:3] = [255,0,0,20]   #draw axes at corner of box 
      d2[0:3, :, 0:3] = [0,255,0,20]
      d2[0:3, 0:3, :] = [0,0,255,20]    
      self.image3DVol=gl.GLVolumeItem(d2)
      self.image3DVol.translate(-128,-128,-128)
      self.view3Dwin.addItem(self.image3DVol)
      #self.view3Dwin.update(self.geometry())      
      #self.view3Dwin.repaint(self.geometry())
        

  def mouseMoved(self,evt): 
    '''mouse move event to move crosshairs and display location and values'''
    pos = evt[0]  ## using signal proxy turns original arguments into a tuple
    if self.imv.view.sceneBoundingRect().contains(pos):
        mousePoint = self.imv.view.vb.mapSceneToView(pos)
        self.ui.lblH.setText("{:.2f}".format(mousePoint.x()))
        self.ui.lblV.setText("{:.2f}".format(mousePoint.y()))
        if abs(mousePoint.x()) < self.ds.FoVX[self.nCurrentImage]/2 and abs(mousePoint.y()) < self.ds.FoVY[self.nCurrentImage]/2:
          Xindex = int((mousePoint.x()+self.ds.FoVX[self.nCurrentImage]/2)/self.ds.PixelSpacingX[self.nCurrentImage]) #if self.ds.PixelSpacingX[self.nCurrentImage] > 0. else Xindex = int(mousePoint.x())
          Yindex = int((mousePoint.y()+self.ds.FoVY[self.nCurrentImage]/2)/self.ds.PixelSpacingY[self.nCurrentImage]) #if self.ds.PixelSpacingY[self.nCurrentImage] > 0. else Yindex = int(mousePoint.y())
          value=  self.ds.PA[self.nCurrentImage][Xindex,Yindex]      
          self.ui.lblValue.setText("{:.2f}".format(value))
          rc= self.reltoGlobal(mousePoint.x(), mousePoint.y(), self.nCurrentImage)
          self.ui.lblX.setText("{:.2f}".format(rc[0]))
          self.ui.lblY.setText("{:.2f}".format(rc[1]))
          self.ui.lblZ.setText("{:.2f}".format(rc[2]))
        self.imv.vLine.setPos(mousePoint.x())
        self.imv.hLine.setPos(mousePoint.y()) 

  def reltoGlobal (self, h,v,n):   #given relative coordinate h,v of image n returns np vector of global coordinates 
    #rc= ((h+self.ds.FoVX[n]/2) * self.ds.RowDirection[n]+(v+self.ds.FoVX[n]/2)*self.ds.ColumnDirection[n])+self.ds.ImagePosition[n]
    rc= (h* self.ds.RowDirection[n]+v*self.ds.ColumnDirection[n])
    return rc

  def GlobaltoRel(self,r,n):    #Given r vector in global coordinates returns h,v in image plane of image n
    h=np.dot(r,self.ds.RowDirection[n])  
    v=np.dot(r,self.ds.ColumnDirection[n])
#    h=np.dot(r-self.ds.ImageCenter[n],self.ds.RowDirection[n])  
#    v=np.dot(r-self.ds.ImageCenter[n],self.ds.ColumnDirection[n])
    return [h,v]
   
  def DirectionLabel (self,Vector): #returns a direction label corresponding to input vector
      Label = ""
      if abs(Vector[0])> 0.01:
          Label = "{:.2f}".format(Vector[0])  + "X "
      if abs(Vector[1])> 0.01:
          Label += "+  " + "{:.2f}".format(Vector[1]) +"Y  "          
      if abs(Vector[2])> 0.01:
          Label += "+  " + "{:.2f}".format(Vector[2]) +"Z"          
      return Label       

  def showRawData(self):
    '''Plots ROI signal vs relevant parameter; outputs data in self.rdx and self.rdy'''
    self.ui.txtResults.clear()
    self.msgPrint (self.imageDirectory + "\n") 
    self.msgPrint ("Data Type = " + self.dataType + "\n") 
    self.msgPrint ("Raw data: " + time.strftime("%c") + os.linesep)
    self.rdPlot.clear()
    if self.bAllSlices == True:   #analyze all slices together
      self.reducedImageSet= range(1,len(self.ds.PA))
      self.msgPrint ("Slice locations(mm)=" + str(self.ds.SliceLocation[1:]) + "\n")
    else:   # only analyze images which are at the current slice location
      currentSL = self.ds.SliceLocation[self.nCurrentImage]   
      self.reducedImageSet= [i for i, val in enumerate(self.ds.SliceLocation)if val == currentSL]
      self.msgPrint ("Slice location(mm)=" + "{:6.1f}".format(self.ds.SliceLocation[self.nCurrentImage]) + "\n")   
    rd = np.zeros((len(self.pgROIs),len(self.reducedImageSet)))
# Set independent variable (parameter that is being varied ie TI, TE, TR, b etc
# T1 data
    if self.dataType == "T1":
      if self.ui.tabT1.currentIndex() == 0: #T1 Inversion Recovery
        self.rdPlot.setLogMode(x=False,y=True)
        self.rdPlot.setLabel('bottom', "TI(ms)")
        self.rdx = np.array([self.ds.TI[i] for i in self.reducedImageSet])
        self.msgPrint ( "TI(ms)=")
        for ti in self.rdx: 
          self.msgPrint ( "{:12.1f}".format(ti))
      if self.ui.tabT1.currentIndex() == 1: #T1 VFA
        self.rdPlot.setLogMode(x=False,y=False)
        self.rdPlot.setLabel('bottom', "FA(deg)")
        self.rdx = np.array([self.ds.FA[j] for j in self.reducedImageSet])
        self.msgPrint ( "FA(deg)=")
        for fa in self.rdx: 
          self.msgPrint ( "{:12.1f}".format(fa))
      if self.ui.tabT1.currentIndex() == 2: #T1 VTR
        self.rdPlot.setLogMode(x=False,y=False)
        self.rdPlot.setLabel('bottom', "TR(ms)")
        self.rdx = np.array([self.ds.TR[j] for j in self.reducedImageSet])
        self.msgPrint ( "TR(ms)=")
        for tr in self.rdx: 
          self.msgPrint ( "{:12.1f}".format(tr))     
      self.msgPrint (os.linesep)
#T2 Data
    if self.dataType == "T2":
      self.rdPlot.setLogMode(x=False,y=True)
      self.rdPlot.setLabel('bottom', "TE(ms)")
      self.rdx = np.array([self.ds.TE[i] for i in self.reducedImageSet])
      self.msgPrint ( "TE(ms)=")
      for te in self.rdx: 
        self.msgPrint ( "{:12.1f}".format(te))
      self.msgPrint (os.linesep)
#Diffusion Data
    if self.dataType == "Dif":
      if self.ui.tabDif.currentIndex() == 0: #fit signal vs b-value
        self.ADCmap = False
        self.rdPlot.setLogMode(x=False,y=True)
        self.rdPlot.setLabel('bottom', "b(s/mm^2)")
        self.rdx = np.array([self.ds.bValue[i] for i in self.reducedImageSet])
        self.msgPrint ( "b(s/mm^2)=")
        for b in self.rdx: 
          self.msgPrint ( "{:12.1f}".format(b))
        self.msgPrint (os.linesep)
      if self.ui.tabDif.currentIndex() == 1: #ADC map
        self.ADCmap = True
        self.rdPlot.setLogMode(x=False,y=False)
        self.rdPlot.setLabel('bottom', "ROI")
        self.rdx = np.array([roi.Index for roi in self.currentROIs.ROIs])
#PD Data
    if self.dataType == "PD-SNR":
      self.rdPlot.setLogMode(x=False,y=False)
      self.rdx = np.array([roi.PD for roi in self.currentROIs.ROIs])
      self.msgPrint ( "PD(%)=")
      for pd in self.rdx: #note that the first image is a blank dummy
        self.msgPrint ( "{:12.1f}".format(pd))
      self.msgPrint (os.linesep)
#Set and Plot raw signal data  
    for i, roi in enumerate(self.pgROIs):
      self.msgPrint ("ROI-" +"{:02d}".format(i+1) + '    ') 
      for j, pa in enumerate([self.ds.PA[k] for k in self.reducedImageSet]):
        array = roi.getArrayRegion(pa,self.imv.getImageItem())    
        rd[i ,j]= (array.mean()-self.ds.ScaleIntercept[self.reducedImageSet[j]])/self.ds.ScaleSlope[self.reducedImageSet[j]] #corrects for scaling in Phillips data
        self.msgPrint ( "{:12.1f}".format(rd[i,j]) )
      c = self.rgb_to_hex(self.setPlotColor(i))
      if self.dataType in ["T1" , "T2", "Dif"] and not self.ADCmap:
        self.rdPlot.plot(self.rdx, rd[i,:],pen=self.setPlotColor(i),symbolBrush=self.setPlotColor(i), symbolPen='w', name=self.currentROIs.ROIs[i].Name)    
        self.ui.lblRdLegend.insertHtml('<font size="5" color=' + c + '>' + u"\u25CF" + '</font>' + self.currentROIs.ROIs[i].Name + '<BR>'  )  #u"\u25CF"  + '<BR>' 
      self.msgPrint (os.linesep)
    if self.dataType == "PD": #raw data is a 1d array signal vs ROI.PD
        self.rdPlot.plot(self.rdx, rd[:,0],pen=self.setPlotColor(0),symbolBrush=self.setPlotColor(0), symbolPen='w', name=self.currentROIs.ROIs[0].Name)
    if self.dataType == "Dif" and self.ADCmap: #raw data is a 1d array signal vs ROI.Index
        for k in range(len(self.reducedImageSet)):
          self.rdPlot.plot(self.rdx, rd[:,k],pen=self.setPlotColor(0),symbolBrush=self.setPlotColor(0), symbolPen='w', name=self.currentROIs.ROIs[0].Name)    
    self.rdy = rd   #returns a numpy array of raw data
    self.background=0 #set background counts for fits
    if hasattr(self.Phantom, "SNRROIs"):    #obtain background from signal free region (SNR ROI)
      self.rdBackground=np.zeros(len(self.reducedImageSet))
      for j, pa in enumerate([self.ds.PA[k] for k in self.reducedImageSet]):
        roi=self.snrROI
        array = roi.getArrayRegion(pa,self.imv.getImageItem())
        self.rdBackground[j]= (np.average(array)-self.ds.ScaleIntercept[self.reducedImageSet[j]])/self.ds.ScaleSlope[self.reducedImageSet[j]] 
      self.background=np.average(self.rdBackground)
      self.ui.lblBackGround.setText(str(self.background))
       
  def fitData(self):
      if self.dataType == "T1":
        self.resultsPlot.setLogMode(x=False,y=True)
        if self.ui.tabT1.currentIndex() == 0: #T1 Inversion Recovery
          self.fitT1IRData(self.rdx,self.rdy)   #
        if self.ui.tabT1.currentIndex() == 1: #T1 Variable Flip Angle
          self.fitT1VFAData(self.rdx,self.rdy)   #
        if self.ui.tabT1.currentIndex() == 2: #T1 Variable TR repetition time
          self.fitT1VTRData(self.rdx,self.rdy)   # 
      if self.dataType == "T2":
        self.resultsPlot.setLogMode(x=False,y=True)
        self.fitT2SEData(self.rdx,self.rdy)  
      if self.dataType == "Dif":
        if not self.ADCmap:
          self.resultsPlot.setLogMode(x=False,y=False)
          self.fitDifData(self.rdx,self.rdy) 
        if self.ADCmap:
          self.showADCmap() 
          
  def showADCmap(self):
      self.resultsPlot.clear()
      self.ADCvalues=self.rdy[:,0]/1000
      sr = "ADC map" + "\n"
      for i, roi in enumerate(self.pgROIs):
          self.msgPrint ("{:02d}".format(i+1)+ " " )
          sr = sr + "ROI " + "{:02d}".format(i+1)+os.linesep  #build output report text for detailed fitting info
          self.msgPrint ("{:10.3f}".format(self.ADCvalues[i]) )
      self.resultsPlot.plot(np.arange(len(self.pgROIs))+1, self.ADCvalues,pen=self.setPlotColor(7),symbolBrush=self.setPlotColor(7), symbolPen='w')
      self.report =  self.report + self.ui.txtResults.toPlainText() + sr   #add recent results to the beginning of the report 
        
  def fitDifData(self, bValue, data):   
      """Fits Diffusion data, calls fitting routines in DifModel"""
      self.fitx =np.arange(100) * np.amax(bValue) * 1.1 /100  #generate bValues for fit plot
      self.fity=np.zeros((len(self.pgROIs),100))
      self.Difresults=np.zeros((len(self.pgROIs),DifModel.initializeDifModel ()))  #bValue fitting results, first index = ROI, second =ADC, third = S0
      self.Difstderror=np.zeros((len(self.pgROIs),DifModel.initializeDifModel ()))  #array for standard error from fits
      self.msgPrint ("Diffusion fit summary; ADC in mm2/s" + os.linesep)
      self.msgPrint ("ROI  ADC*1000  ADCerr(%)        Si  Sierr(%)" )
      if self.showReferenceValues:
        self.msgPrint ("  ADCref  ADCdev(%)" + os.linesep)
      else:
        self.msgPrint (os.linesep)
      sr = "Diffusion fitting details" + "\n"
      for i, roi in enumerate(self.pgROIs):
          params=DifModel.initializeDifModel (i,bValue, data[i,:],self.currentROIs.ROIs[i], self.useROIValues, self.background)
          pdict=params[0] #parameter dictionary
          plist=params[1] #parameter list   
          out = lmfit.minimize(DifModel.DifModel,pdict,args=(bValue,data[i,:]))
          self.fity[i:]= DifModel.DifModel(pdict, self.fitx, np.zeros(len(self.fitx)))
          self.msgPrint ("{:02d}".format(i+1)+ " " )
          sr = sr + "ROI " + "{:02d}".format(i+1)+os.linesep  #build output report text for detailed fitting info
          for p in plist:
            self.Difresults[i,plist.index(p)]=pdict[p].value #populate output array
            self.Difstderror[i,plist.index(p)]=pdict[p].stderr #populate output array
            if pdict[p].value>0:  #calculate standard error in percent
              se=100*pdict[p].stderr/pdict[p].value
            else:
              se=0
            if p == "ADC":  #multiplier to set ADCs in 10^3mm^2/s
              m=1000.
            else:
              m=1.
            self.msgPrint ("{:10.3f}".format(pdict[p].value*m) + "  " + "{:6.2f}".format(se)+ "  ")
          if self.showReferenceValues:
            self.msgPrint ("{:8.3f}".format(1000*self.currentROIs.ROIs[i].ADC)+ "  " + "{:8.2f}".format((self.Difresults[i,0]-self.currentROIs.ROIs[i].ADC)/self.currentROIs.ROIs[i].ADC*100))
          self.msgPrint (os.linesep)
          sr += lmfit.fit_report(pdict)+os.linesep   #add complete fitting report to output report string
      self.resultsPlot.clear()
      err = pg.ErrorBarItem(x=np.arange(len(self.pgROIs))+1, y=1000*self.Difresults[:,0], top=1000*self.Difstderror[:,0], bottom=1000*self.Difstderror[:,0], beam=0.5)
      self.resultsPlot.addItem(err)
      self.resultsPlot.plot(np.arange(len(self.pgROIs))+1, 1000*self.Difresults[:,0],pen=self.setPlotColor(i),symbolBrush=self.setPlotColor(i), symbolPen='w')
      self.report =  self.report + self.ui.txtResults.toPlainText() + sr   #add recent results to the beginning of the report 
                  
  def fitT2SEData(self, TE, data):   
      """Fits T2-SE data, calls fitting routines in T1SE"""
      self.fitx =np.arange(100) * np.amax(TE) * 1.1 /100  #generate TEs for fit plot
      self.fity=np.zeros((len(self.pgROIs),100))
      self.T2results=np.zeros((len(self.pgROIs),T2SE.initializeT2SE ()))  #TE fitting results, first index = ROI, second index = parameter referred to in T1Params
      self.msgPrint ("T2-SE fit summary" + os.linesep)
      self.msgPrint ("!!! Not fitting points below noise floor =  " + str (self.noisefactor) + " * " +  "{:6.2f}".format(self.background) + "\n" )      
      self.msgPrint ("ROI  T2(ms)  T2err(%)        Si  Sierr(%)         B   Berr(%) T2ref(ms)  T2dev(%)    nFitPoints" + os.linesep)
      sr = "T2-SE fitting details" + "\n"
      for i, roi in enumerate(self.pgROIs):
          params=T2SE.initializeT2SE (i,TE, data[i,:],self.currentROIs.ROIs[i], self.useROIValues, self.background)
          pdict=params[0] #parameter dictionary
          plist=params[1] #parameter list
          d= data[i,:] > self.noisefactor*self.background  
          nfitpoints = len(data[i,d]) 
          out = lmfit.minimize(T2SE.T2SE,pdict,args=(TE[d],data[i,d]))
          self.fity[i:]= T2SE.T2SE(pdict, self.fitx, np.zeros(len(self.fitx)))
          self.msgPrint ("{:02d}".format(i+1)+ " " )
          sr = sr + "ROI " + "{:02d}".format(i+1)+os.linesep  #build output report text for detailed fitting info
          for p in plist:
            self.T2results[i,plist.index(p)]=pdict[p].value #populate output array
            if pdict[p].value>0:  #calculate standard error
              se=100*pdict[p].stderr/pdict[p].value
            else:
              se=0
            self.msgPrint ("{:10.2f}".format(pdict[p].value) + "  " + "{:6.2f}".format(se)+ "  ")
          self.msgPrint ("{:8.2f}".format(self.currentROIs.ROIs[i].T2)+ "  " + "{:8.2f}".format((self.T2results[i,0]-self.currentROIs.ROIs[i].T2)/self.currentROIs.ROIs[i].T2*100) + "      " + str(nfitpoints))
          self.msgPrint (os.linesep)
          sr += lmfit.fit_report(pdict)+os.linesep   #add complete fitting report to output report string
      self.resultsPlot.clear()
      self.resultsPlot.plot(np.arange(len(self.pgROIs))+1, self.T2results[:,0],pen=self.setPlotColor(i),symbolBrush=self.setPlotColor(i), symbolPen='w')
      self.report =self.report +  self.ui.txtResults.toPlainText() + sr   #add recent results to the beginning of the report 
          
  def fitT1VFAData(self,FA,data):
      """Fits T1-VFA data, calls fitting routines in T1VFA"""
      self.T1results=np.zeros((len(self.pgROIs),T1VFA.initializeT1VFA ()))  #T1 fitting results, first index = ROI, second index = parameter referred to in T1Params
      self.fitx =np.arange(100) * np.amax(FA) * 1.1 /100  #generate flip angles for fit plot
      self.fity=np.zeros((len(self.pgROIs),100))
      self.msgPrint ("T1-VFA fit summary" + os.linesep)
      self.msgPrint ("ROI  T1(ms)T1err(%)    S90  S90err(%)    TE(ms)  TEerr        B  Berr(%)")
      if self.showReferenceValues:
        self.msgPrint ("  T1ref(ms) T1dev(%)" + os.linesep)
      else:
        self.msgPrint (os.linesep)
      sr = "T1-VFA fitting details" + "\n"
      for i, roi in enumerate(self.pgROIs):
          params=T1VFA.initializeT1VFA (i,FA, data[i,:],np.array([self.ds.TR[j] for j in self.reducedImageSet])[0] ) #note VFA model needs TR
          pdict=params[0] #parameter dictionary
          plist=params[1] #parameter list   
          out = lmfit.minimize(T1VFA.T1VFA,pdict,args=(FA*np.pi/180.0,data[i,:]))
          self.fity[i:]= T1VFA.T1VFA(pdict, self.fitx*np.pi/180.0, np.zeros(len(self.fitx)))
          self.msgPrint ("{:02d}".format(i+1))
          sr= sr + ("ROI " + "{:02d}".format(i+1)+os.linesep)  #build output report text
          for p in plist:
            self.T1results[i,plist.index(p)]=pdict[p].value #populate output array
            if pdict[p].value>0:
              se=100*pdict[p].stderr/pdict[p].value
            else:
              se=0
            
            self.msgPrint ("{:10.2f}".format(pdict[p].value) + "  " + "{:6.2f}".format(se)+ "  ")
          self.msgPrint ("{:8.2f}".format(self.currentROIs.ROIs[i].T1)+ "  " + "{:8.2f}".format((self.T1results[i,0]-self.currentROIs.ROIs[i].T1)/self.currentROIs.ROIs[i].T1*100))
          self.msgPrint (os.linesep)
          sr += lmfit.fit_report(pdict)+os.linesep
      self.resultsPlot.clear()
      self.resultsPlot.plot(np.arange(len(self.pgROIs))+1, self.T1results[:,0],pen=self.setPlotColor(i),symbolBrush=self.setPlotColor(i), symbolPen='w')
      self.report =self.report +  self.ui.txtResults.toPlainText() + sr
 
  def fitT1VTRData(self,TR,data):
      """Fits T1-VTR data, calls fitting routines in T1VTR"""
      self.T1results=np.zeros((len(self.pgROIs),T1VTR.initializeT1VTR ()))  #T1 fitting results, first index = ROI, second index = parameter referred to in T1Params
      self.fitx =np.arange(100) * np.amax(TR) * 1.1 /100  #generate flip angles for fit plot
      self.fity=np.zeros((len(self.pgROIs),100))
      self.msgPrint ("T1-VTR fit summary" + os.linesep)
      self.msgPrint ("ROI  T1(ms)T1err(%)    S0  S0err(%)    TE(ms)  TEerr        FA  FAerr(%)  T1ref(ms) T1dev(%)" + os.linesep)
      sr = "T1-VTR fitting details" + "\n"
      for i, roi in enumerate(self.pgROIs):
          params=T1VTR.initializeT1VTR (i, TR, data[i,:], self.currentROIs.ROIs[i], self.ds, self.reducedImageSet)  #note VTR model needs FA, TE
          pdict=params[0] #parameter dictionary
          plist=params[1] #parameter list   
          out = lmfit.minimize(T1VTR.T1VTR,pdict,args=(TR,data[i,:]))
          self.fity[i:]= T1VTR.T1VTR(pdict, self.fitx, np.zeros(len(self.fitx)))
          self.msgPrint ("{:02d}".format(i+1))
          sr= sr + ("ROI " + "{:02d}".format(i+1)+os.linesep)  #build output report text
          for p in plist:
            self.T1results[i,plist.index(p)]=pdict[p].value #populate output array
            if pdict[p].value>0:
              se=100*pdict[p].stderr/pdict[p].value
            else:
              se=0
            self.msgPrint ("{:10.2f}".format(pdict[p].value) + "  " + "{:6.2f}".format(se)+ "  ")
          self.msgPrint ("{:8.2f}".format(self.currentROIs.ROIs[i].T1)+ "  " + "{:8.2f}".format((self.T1results[i,0]-self.currentROIs.ROIs[i].T1)/self.currentROIs.ROIs[i].T1*100))
          self.msgPrint (os.linesep)
          sr += lmfit.fit_report(pdict)+os.linesep
      self.resultsPlot.clear()
      self.resultsPlot.plot(np.arange(len(self.pgROIs))+1, self.T1results[:,0],pen=self.setPlotColor(i),symbolBrush=self.setPlotColor(i), symbolPen='w')
      self.report =self.report +  self.ui.txtResults.toPlainText() + sr
      
  def fitT1IRData(self,TI,data):
      """Fits T1-IR data, calls fitting routines in T1IRabs"""
      self.fitx =np.arange(100) * np.amax(TI) * 1.1 /100  #generate TIs for fit plot
      self.fity=np.zeros((len(self.pgROIs),100))
      self.T1results=np.zeros((len(self.pgROIs),T1IRabs.initializeT1IRabs ()))  #T1 fitting results, first index = ROI, second index = parameter referred to in T1Params
      self.msgPrint ("T1-IR fit summary" + os.linesep)
      self.msgPrint ("ROI   T1(ms) T1err(%)        Si  Sierr(%)       B    Berr(%)  T1ref(ms)   T1dev(%)" + os.linesep)
      sr = "T1-IR fitting details" + "\n"
      for i, roi in enumerate(self.pgROIs):
          params=T1IRabs.initializeT1IRabs (i,TI, data[i,:],self.currentROIs.ROIs[i], self.useROIValues)
          pdict=params[0] #parameter dictionary
          plist=params[1] #parameter list   
          out = lmfit.minimize(T1IRabs.T1IRabs,pdict,args=(TI,data[i,:]))
          self.fity[i:]= T1IRabs.T1IRabs(pdict, self.fitx, np.zeros(len(self.fitx)))
          self.msgPrint ("{:02d}".format(i+1)+ " " )
          sr = sr + "ROI " + "{:02d}".format(i+1)+os.linesep  #build output report text for detailed fitting info
          for p in plist:
            self.T1results[i,plist.index(p)]=pdict[p].value #populate output array
            self.msgPrint ("{:10.2f}".format(pdict[p].value) + "  " + "{:6.2f}".format(100*pdict[p].stderr/pdict[p].value)+ "  ")
          if self.showReferenceValues:
            self.msgPrint ("{:8.2f}".format(self.currentROIs.ROIs[i].T1)+ "  " + "{:8.2f}".format((self.T1results[i,0]-self.currentROIs.ROIs[i].T1)/self.currentROIs.ROIs[i].T1*100))
          self.msgPrint (os.linesep)
          sr += lmfit.fit_report(pdict)+os.linesep   #add complete fitting report to output report string
      self.resultsPlot.clear()
      self.resultsPlot.plot(np.arange(len(self.pgROIs))+1, self.T1results[:,0],pen=self.setPlotColor(i),symbolBrush=self.setPlotColor(i), symbolPen='w')
      self.report =self.report +  self.ui.txtResults.toPlainText() + sr   #add recent results to the beginning of the report 
      
  def viewFits(self):
        """Opens FitPlot window to display quality of fits"""
        if hasattr(self,"viewFitsWindow")==False:
          self.viewFitsWindow=FitPlots.FitPlots(self.rdx, self.rdy, self.fitx, self.fity)
          self.viewFitsWindow.setWindowTitle("View Fits:" + self.dataType + "  analysis")
        else:
          self.viewFitsWindow.__init__(self.rdx, self.rdy, self.fitx, self.fity)
          self.viewFitsWindow.setWindowTitle("View Fits:" + self.dataType + "  analysis")
        self.viewFitsWindow.show()
        
  def outputReport(self):
        if hasattr(self,"reportwindow")==False:
          self.reportwindow=Report.Report(self)
          self.reportwindow.setWindowTitle("Report:" + self.dataType + "  analysis")
        self.reportwindow.show()
        self.reportwindow.printReport(self.report)
        
  def saveReport(self):
      fileName = QtGui.QFileDialog.getSaveFileName(parent=None, caption="Report File Name", directory = '', selectedFilter = ".dat")
      if not fileName:  #if cancel is pressed return
        return None
      f= open(fileName, 'w')
      self.Phantom.ROIsets[0]=self.currentROIs
      f.write(self.report)
      f.close()
      
  def clearReport(self):
      self.report = "" 
      if hasattr(self,"reportwindow")==True:
        self.reportwindow.printReport(self.report)   
             
  def setPlotColor(self,i):
      color = (int(np.base_repr(i, base=3, padding=3)[-1])*127, int(np.base_repr(i, base=3, padding=3)[-2])*127,int(np.base_repr(i, base=3, padding=3)[-3])*127)
      return color

  def rgb_to_hex(self,rgb):
    return '#%02x%02x%02x' % rgb
   
  def T1Analysis(self):
      self.dataType = "T1"
      self.setDataType(self.dataType)
          
  def T2Analysis(self):
      self.dataType = "T2"
      self.setDataType(self.dataType)
         
  def PDSNRAnalysis(self):
      self.dataType = "PD-SNR"
      self.setDataType(self.dataType)
       
  def diffusionAnalysis(self):
      self.dataType = "Dif"
      self.setDataType(self.dataType)
           
  def setDataType(self,dataType):
    if dataType == "T1":
      self.ui.stackedModels.setCurrentIndex(0)
      self.setWindowTitle(self.wTitle + 'T1 Analysis')
      self.rdPlot.setTitle("T1 raw data")
      self.rdPlot.setLabel('left', "Ave. Counts", units='A')
      self.rdPlot.setLabel('bottom', "TI(ms)")
      self.resultsPlot.setLabel('bottom', "ROI")
      self.resultsPlot.setLabel('left', "T1(ms)")
      self.resultsPlot.setTitle("T1 Results")
      self.roiPen = pg.mkPen('g', width=3)
    if dataType == "T2":
      self.ui.stackedModels.setCurrentIndex(1)
      self.setWindowTitle(self.wTitle + 'T2 Analysis')
      self.rdPlot.setTitle("T2 raw data")
      self.rdPlot.setLabel('left', "Ave. Counts", units='A')
      self.rdPlot.setLabel('bottom', "TE")
      self.resultsPlot.setLabel('bottom', "ROI")
      self.resultsPlot.setLabel('left', "T2(ms)")
      self.resultsPlot.setTitle("T2 Results")
      self.roiPen = pg.mkPen('r', width=3)
    if dataType == "PD-SNR":
      self.ui.stackedModels.setCurrentIndex(2)
      self.setWindowTitle(self.wTitle + 'Proton Density/ SNR Analysis')
      self.rdPlot.setTitle("PD raw data")
      self.rdPlot.setLabel('left', "Ave. Counts", units='A')
      self.rdPlot.setLabel('bottom', "PD(%)E")
      self.resultsPlot.setTitle("PD Results")
      self.roiPen = pg.mkPen('y', width=3)
      self.ROIset = "PDArray"   #determines which ROI set to use via ROIsetdict 
      self.InitialROIs = self.Phantom.ROIsets[2]     #Current ROIs are initial ROIs with global rotation and translation
      self.resetROIs()
      self.useROIValues = True
    if dataType == "Dif":
      self.ui.stackedModels.setCurrentIndex(3)
      self.setWindowTitle(self.wTitle + 'Diffusion Analysis')
      self.rdPlot.setTitle("Diffusion raw data")
      self.rdPlot.setLabel('left', "Ave. Counts", units='A')
      self.rdPlot.setLabel('bottom', "b(s/mm^2)")
      self.resultsPlot.setLabel('bottom', "ROI")
      self.resultsPlot.setLabel('left', "ADC*1000(mm^2/s)")
      self.resultsPlot.setTitle("Diffusion Results")
      self.roiPen = pg.mkPen('b', width=3)
    if dataType == "":
      self.setWindowTitle(self.wTitle)
      self.rdPlot.setLabel('left', "Counts", units='A')
      self.rdPlot.setLabel('bottom', "X Axis")
      self.rdPlot.setTitle("Raw Data")
      self.rdPlot.clear()
      self.resultsPlot.clear()
      self.resultsPlot.setLabel('bottom', "X Axis", units='s')
      self.resultsPlot.setTitle("Results")
      self.roiPen = pg.mkPen('p', width=3)      

  def msgPrint (self, s):
          self.ui.txtResults.insertPlainText(s)

class fCircleROI(pg.EllipseROI):
    """Defines a circular ROI using pyqtgraph's EllipseROI"""
    def __init__(self, callingform, pos, size, label,   **args):   #passing in calling form, could be a problem
        pg.ROI.__init__(self, pos, size, **args)
        self.aspectLocked = True
        self.ROIViewInstance=callingform
        self.Index = 0
        self.label = pg.TextItem(label, callingform.lblColor, anchor = (0,0))
        self.label.setPos(pos[0],pos[1])
        self.label.setFont(callingform.lblFont)

    def getArrayRegion(self, arr, img=None):
        arr = pg.ROI.getArrayRegion(self, arr, img)
        if arr is None or arr.shape[0] == 0 or arr.shape[1] == 0:
            return None
        w = arr.shape[0]
        h = arr.shape[1]
        ## generate an ellipsoidal mask
        mask = np.fromfunction(lambda x,y: (((x+0.5)/(w/2.)-1)**2+ ((y+0.5)/(h/2.)-1)**2)**0.5 < 1, (w, h))
        maskedArr = ma.masked_array(arr, mask)
        return maskedArr

    def mouseDragEvent(self, ev):       #Dragging ROI event: translates ROIs
        if ev.isStart():  
            if ev.button() == QtCore.Qt.LeftButton:
                self.setSelected(True)
                if self.translatable:
                    self.isMoving = True
                    self.preMoveState = self.getState()
                    self.cursorOffset = self.pos() - self.mapToParent(ev.buttonDownPos())
                    self.sigRegionChangeStarted.emit(self)
                    ev.accept()
                else:
                    ev.ignore()
        elif ev.isFinish():
            if self.translatable:
                if self.isMoving:
                    self.stateChangeFinished()
                self.isMoving = False
            return
        if self.translatable and self.isMoving and ev.buttons() == QtCore.Qt.LeftButton:
            snap = True if (ev.modifiers() & QtCore.Qt.ControlModifier) else None
            newPos = self.mapToParent(ev.pos()) + self.cursorOffset
#            self.translate(newPos - self.pos(), snap=snap, finish=False)
            self.ROIViewInstance.translateROIs(newPos - self.pos(),snap, self.Index)

    def setMouseHover(self, hover):
        '''Inform the ROI that the mouse is(not) hovering over it'''
        if self.mouseHovering == hover:
            return
        self.mouseHovering = hover
        if hover:
            self.currentPen = fn.mkPen(255, 255, 0)
            array = self.getArrayRegion(self.ROIViewInstance.ds.PA[self.ROIViewInstance.nCurrentImage],self.ROIViewInstance.imv.getImageItem())
            mean=array.mean()
            std=array.std()
            self.ROIViewInstance.currentROI=self.ROIViewInstance.currentROIs.ROIs[self.Index-1]           
            self.ROIViewInstance.currentROI.SignalAve= mean
            self.ROIViewInstance.currentROI.SignalRMS= std
            self.ROIViewInstance.showROIInfo()
        else:
            self.currentPen = self.pen
            #self.ROIViewInstance.currentROI=-1
        self.update() 
        
#     def trimCircularROI(self,array):
#       '''trims excess 0-value pixels from 2-d array and returns a 1-d array of values within circular ROI'''
#       nz =np.count_nonzero(array)
#       outarray = np.array([])    
#       # rx=array.shape[0]/2
#       # ry=array.shape[1]/2
#       # r=rx- 0.5
#       # for (i,j), value in np.ndenumerate(array):
#       #   if (i+0.5-rx)**2 + (j+0.5-ry)**2 <= r**2:
# 
#       for i in range(array.shape[0]):
#         outarray=np.append(outarray,np.trim_zeros(array[i]) )
#       if outarray.size<> nz:
#         print "ROI trim problem: # of output array zero elements= " + str(outarray.size - np.count_nonzero(outarray)) 
#         print "ROI trim problem: # of nonzero input array elememnts - # output array elements " + str(nz - outarray.size)
#       return outarray
    
class imageStackWindow(ROIView):
  def __init__(self, rv, parent = None):
    '''Define image stack windows and menus, rv is the parent ROIView window'''    
    super(ROIView, self).__init__()
    self.win = QtGui.QMainWindow()
    self.win.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    self.win.resize(800,600)
    self.imv = pg.ImageView( view = pg.PlotItem())
    self.win.setCentralWidget(self.imv)
    self.win.setWindowTitle('Image Stack')
    point = self.rect().topRight()
    self.win.move(point + QtCore.QPoint(self.width()/2, 0)) 
    self.menu = self.win.menuBar()
    self.imageMenu = self.menu.addMenu('&Images')
    self.actionSelectImages = QtGui.QAction('Select/Add Images', self)
    self.actionSelectImages.setShortcut('Ctrl+S')
    self.actionSelectImages.setStatusTip('Select/Add Images')
    self.actionSelectImages.triggered.connect(rv.openFile)
    self.imageMenu.addAction(self.actionSelectImages) 
    self.actionClear_All_Images = QtGui.QAction('Clear All Images', self)
    self.actionClear_All_Images.setShortcut('Ctrl+C')
    self.actionClear_All_Images.setStatusTip('Clear All Images')
    self.actionClear_All_Images.triggered.connect(rv.clearImages)
    self.imageMenu.addAction(self.actionClear_All_Images)
           
    self.phantomMenu = self.menu.addMenu('&Phantoms')
    self.actionOpenPhantomFile = QtGui.QAction('Open phantom file', self)
    self.actionOpenPhantomFile.setStatusTip('Open phantom file')
    self.actionOpenPhantomFile.triggered.connect(rv.openPhantomFile)
    self.phantomMenu.addAction(self.actionOpenPhantomFile)
    self.actionSavePhantomFile = QtGui.QAction('Save phantom file', self)
    self.actionSavePhantomFile.setStatusTip('Save phantom file')
    self.actionSavePhantomFile.triggered.connect(rv.savePhantomFile)
    self.phantomMenu.addAction(self.actionSavePhantomFile)  
    
    self.actionSystemPhantom = QtGui.QAction('System Phantom', self)
    self.actionSystemPhantom.setStatusTip('System Phantom')
    self.actionSystemPhantom.triggered.connect(rv.SystemPhantom)
    self.phantomMenu.addAction(self.actionSystemPhantom) 
    self.actionDiffusionPhantom = QtGui.QAction('Diffusion Phantom', self)
    self.actionDiffusionPhantom.setStatusTip('Diffusion Phantom')
    self.actionDiffusionPhantom.triggered.connect(rv.DiffusionPhantom)
    self.phantomMenu.addAction(self.actionDiffusionPhantom) 
    self.actionBreastPhantom = QtGui.QAction('Breast Phantom', self)
    self.actionBreastPhantom.setStatusTip('Breast Phantom')
    self.actionBreastPhantom.triggered.connect(rv.BreastPhantom)
    self.phantomMenu.addAction(self.actionBreastPhantom) 
    self.actionNISThcpPhantom = QtGui.QAction('NIST hcp Phantom', self)
    self.actionNISThcpPhantom.setStatusTip('NIST hcp Phantom')
    self.actionNISThcpPhantom.triggered.connect(rv.NISThcpPhantom)
    self.phantomMenu.addAction(self.actionNISThcpPhantom)
    self.actionNISThcpCoronalPhantom = QtGui.QAction('NIST hcp Coronal Phantom', self)
    self.actionNISThcpCoronalPhantom.setStatusTip('NIST hcp Coronal Phantom')
    self.actionNISThcpCoronalPhantom.triggered.connect(rv.NISThcpCoronalPhantom)
    self.phantomMenu.addAction(self.actionNISThcpCoronalPhantom) 
    self.actionShowPhantomProperties = QtGui.QAction('Current phantom info', self)
    self.actionShowPhantomProperties.setStatusTip('Current phantom info')
    self.actionShowPhantomProperties.triggered.connect(rv.showPhantomProperties)
    self.actionShowPhantomProperties.setShortcut('Ctrl+P')
    self.phantomMenu.addAction(self.actionShowPhantomProperties)   
    
    self.roiMenu = self.menu.addMenu('&ROIs')
    self.imv.getView().setLabel('bottom',"H","mm")
    self.imv.getView().setLabel('left',"V","mm")

class phantomImageWindow(ROIView):
  def __init__(self, fname, parent = None):
    '''Defines image stack windows and menus, rv is the parent ROIVIew window'''    
    super(ROIView, self).__init__()
    self.win = QtGui.QMainWindow()
    self.win.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    self.win.resize(800,600)
    self.win.setWindowTitle('Current Phantom')
    self.setStyleSheet("background-image: url(" + str(fname) + "); background-repeat: no-repeat; background-position: center;")
    #self.win.setCentralWidget(self.imv)
                      
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    main = ROIView("T1")
    main.show()
    sys.exit(app.exec_())

    