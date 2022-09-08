import os, logging, time
import cv2
import numpy as np
logger = logging.getLogger(__name__)
class Greeting:
    def __init__(self):
        logger.debug('Here we go')
        self.greet()
        time.sleep(3)
        logger.debug('Loaded')
        
    def greet(self,*args):
        print("""

     ____________________________
    /                           /\ 
   /   Hey, Jiamin            _/ /\ 
  /    How's it going?       / \/
 /                           /\     
/___________________________/ /     
\___________________________\/ 
 \ \ \ \ \ \ \ \ \ \ \ \ \ \ \
 
 """)
    
    def garf(self,*args):
        im = cv2.imload(r'C:\Users\iHR 550\Documents\ModuleServer\mymodules\garf.png')
        im_ar = np.asarray(im)
        return im_ar.tolist()
