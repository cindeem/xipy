from xipy.vis import mayavi_widgets
from xipy.vis import mayavi_tools
from xipy.overlay.image_overlay import ImageOverlayManager
from xipy.slicing import load_resampled_slicer
from xipy import TEMPLATE_MRI_PATH

from PyQt4 import QtCore, QtGui
import sys
if QtGui.QApplication.startingUp():
    app = QtGui.QApplication(sys.argv)
else:
    app = QtGui.QApplication.instance() 

anat = load_resampled_slicer(TEMPLATE_MRI_PATH)
func = load_resampled_slicer('map_img.nii')

func_man = ImageOverlayManager(anat.bbox, overlay=func)

win = mayavi_widgets.MayaviWidget(functional_manager=func_man)
win.mr_vis.anat_image = anat

from mini_track_control import mini_track_feature
mf = mini_track_feature(my_track_file, mayavi_win=win.mr_vis)
mf.edit_traits()

win.show()
app.exec_()
