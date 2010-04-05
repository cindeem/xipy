from PyQt4 import QtGui, QtCore
from xipy.overlay.plugins import all_registered_plugins

class XIPYWindowApp(QtGui.QMainWindow):
    _active_tools = []

    # these must be populated by the subclass app
    _plugin_args = ()
    _plugin_kwargs = dict()

    plugin_launched = QtCore.pyqtSignal(object)

    def __init__(self, image=None, parent=None, designer_layout=None):
        super(XIPYWindowApp, self).__init__(parent=parent)
        print designer_layout
        if designer_layout:
            # kick in the Qt Designer generated layout and callback connections
            designer_layout.setupUi(self)
            # consume the layout object
            self.__dict__.update(designer_layout.__dict__)
        else:
            print 'no layout helper'

        # do some boilerplate UI stuff if it isn't already here
        if not hasattr(self, 'menubar'):
            self.menubar = QtGui.QMenuBar(self)
        if not hasattr(self, 'menuTools'):
            self.menuTools = QtGui.QMenu(self.menubar)
            self.menuTools.setObjectName("menuTools")
            self.menubar.addAction(self.menuTools.menuAction())
            self.menuTools.setTitle(
                QtGui.QApplication.translate(
                    self.objectName(), "Tools",
                    None, QtGui.QApplication.UnicodeUTF8
                    )
                )
        if not hasattr(self, 'menuView'):
            self.menuView = QtGui.QMenu(self.menubar)
            self.menuView.setObjectName("menuView")
            self.menubar.addAction(self.menuView.menuAction())
            self.menuView.setTitle(
                QtGui.QApplication.translate(
                    self.objectName(), "View",
                    None, QtGui.QApplication.UnicodeUTF8
                    )
                )

        self.create_plugin_options()
    
    def create_plugin_options(self):
        pitems = all_registered_plugins()
        for pname, pclass in pitems:
            action = QtGui.QAction(self)
            action.setObjectName('action'+pname.replace(' ', '_'))
            callback = pclass.request_launch_callback(
                self._launch_plugin_tool
                )
            action.triggered.connect(callback)
            self.menuTools.addAction(action)
            action.setText(
                QtGui.QApplication.translate(
                    self.objectName(), pname,
                    None, QtGui.QApplication.UnicodeUTF8
                    )
                )
##             action.setText(pname)

    def _launch_plugin_tool(self, pclass, *args):
        if not self._plugin_args:
            msg = 'There are no plugin arguments specified in this app'
            raise ValueError(msg)
        
##         loc_methods = (self.ortho_figs_widget.update_location, )
##         image_methods = (self.triggered_overlay_update, )
##         im_props_methods = (self.change_overlay_props, )
##         out_loc_signal = self.ortho_figs_widget.xyz_state[float,float,float]
        active_tool = filter(lambda x: type(x)==pclass, self._active_tools)
        if active_tool:
            print 'already launched this tool, so make it active (eventually)'
            tool = active_tool[0]
            print tool
            return
        tool = pclass(*self._plugin_args, **self._plugin_kwargs)

##         tool = pclass(loc_methods, image_methods, im_props_methods,
##                       self.image.bbox, main_ref=self,
##                       external_loc=out_loc_signal)
##         # go ahead and emit location signal to flush everything through
##         out_loc_signal.emit(*self.ortho_figs_widget.active_voxel)

        tool.show()
        tool.activateWindow()
        toggle = tool.toggle_view_action()
        self.menuView.addAction(toggle)
        self._active_tools.append(tool)
        self.plugin_launched.emit(tool)

        
