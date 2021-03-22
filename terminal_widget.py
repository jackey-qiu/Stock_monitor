import numpy as np
from pyqtgraph.console import ConsoleWidget
import pyqtgraph as pg
from pyqtgraph import QtGui

class TerminalWidget(ConsoleWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.localNamespace['pg'] = pg
        self.localNamespace['np'] = np

    def update_name_space(self, name, new_object):
        self.localNamespace[name] = new_object

    def write(self, strn, html=False):                                          
        self.output.moveCursor(QtGui.QTextCursor.End)                           
        if html:                                                                
            self.output.textCursor().insertHtml(strn)                           
        else:                                                                   
            if self.inCmd:                                                      
                self.inCmd = False                                              
                self.output.textCursor().insertHtml("</div><br><div style='font-weight: normal; background-color:white;color:blue'>")
                # self.stdout.write("</div><br><div style='font-weight: normal; background-color: #FFF;'>")
            self.output.insertPlainText(strn) 