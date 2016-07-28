
"""
Created on Jan 7, 2015
Each model is referred to using a modelname and must contain must contain three methods
  intializemodelname
  modelname
  fitmodelname
T1VFA : T1 variableflip angle  model 
last modification: 
"""

import lmfit
import numpy as np


def initializeT1VFA (nroi=None,FA=None, data=None, TR=10000):    
    """initialize parameters for T1 variable flip angle model"""
    nT1VFAparams =4      #max number of parameters, some may be fixed
    if nroi == None:    #if no parameters are passed return the number of fitting parameters for this model
      return nT1VFAparams
    T1params = lmfit.Parameters()   #define parameter dictionary
    paramlist = []    # list of parameters used for this model
    T1guess=100
    T1params.add('T1', value= T1guess, min=5, vary = True)
    paramlist.append('T1')
    T1params.add('S90', value= np.amax(data),min=0, vary = True)
    paramlist.append('S90')
    T1params.add('TR', value= TR, vary = False)
    paramlist.append('TR')
    T1params.add('B',  value= 0,  min=0,  vary = False)
    paramlist.append('B')
    return [T1params,paramlist]

# define objective function: returns the array to be minimized
def T1VFA(params, FA, data):  #note flip angles FA must be in radians
    """ T1-VFA model ; FA flip angle array, T1 recovery time"""
    B = params['B'].value
    S90 = params['S90'].value
    T1 = params['T1'].value
    TR = params['TR'].value
    model = S90 * np.sin(FA) * (1 - np.exp(-TR / T1)) / (1 - np.exp(-TR / T1) * np.cos(FA)) + B
    return (model - data)

def fitT1VFA(params, FA, data):
    """fits signal vs TI data to T1IRabs model"""
    result = lmfit.minimize(T1VFA, params, args=(FA, data))
    final = data + result.residual
    return final
