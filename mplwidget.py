# ------------------------------------------------------
# -------------------- mplwidget.py --------------------
# ------------------------------------------------------
from PyQt5.QtWidgets import*
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)
    
class MplWidget(QWidget):
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)   
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig) 
        self.navi_toolbar = NavigationToolbar(self.canvas, self)
        vertical_layout = QVBoxLayout()
        vertical_layout.addWidget(self.canvas)
        vertical_layout.addWidget(self.navi_toolbar)
        # self.canvas.ax_img = self.canvas.figure.add_subplot(121)
        # self.canvas.ax_profile = self.canvas.figure.add_subplot(322)
        # self.canvas.ax_ctr = self.canvas.figure.add_subplot(324)
        # self.canvas.ax_pot = self.canvas.figure.add_subplot(326)
        #self.canvas.axes = self.canvas.figure.add_subplot(111)
        self.setLayout(vertical_layout)

    def update_canvas(self):
        self.canvas = FigureCanvas(Figure()) 
        self.navi_toolbar = NavigationToolbar(self.canvas, self)
        vertical_layout = QVBoxLayout()
        vertical_layout.addWidget(self.canvas)
        vertical_layout.addWidget(self.navi_toolbar)
        # self.canvas.ax_img = self.canvas.figure.add_subplot(121)
        # self.canvas.ax_profile = self.canvas.figure.add_subplot(322)
        # self.canvas.ax_ctr = self.canvas.figure.add_subplot(324)
        # self.canvas.ax_pot = self.canvas.figure.add_subplot(326)
        #self.canvas.axes = self.canvas.figure.add_subplot(111)
        self.setLayout(vertical_layout)