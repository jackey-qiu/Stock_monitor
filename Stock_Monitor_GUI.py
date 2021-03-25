import sys,os,qdarkstyle
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
from PyQt5 import uic
import random
import numpy as np
import matplotlib.pyplot as plt
# import finplot as fplt
try:
    from . import locate_path
    from . import data_extractor
except:
    import locate_path
    import data_extractor
script_path = locate_path.module_path_locator()
sys.path.append(script_path)
sys.path.append(os.path.join(script_path,'lib'))
import pandas as pd
import time
import matplotlib
from matplotlib.ticker import AutoMinorLocator
from matplotlib.ticker import FixedLocator, FixedFormatter
os.environ["QT_MAC_WANTS_LAYER"] = "1"
# matplotlib.use("TkAgg")
from scipy import signal
# import scipy.signal.savgol_filter as savgol_filter
import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui
import datetime

#from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)
def error_pop_up(msg_text = 'error', window_title = ['Error','Information','Warning'][0]):
    msg = QMessageBox()
    if window_title == 'Error':
        msg.setIcon(QMessageBox.Critical)
    elif window_title == 'Warning':
        msg.setIcon(QMessageBox.Warning)
    else:
        msg.setIcon(QMessageBox.Information)

    msg.setText(msg_text)
    # msg.setInformativeText('More information')
    msg.setWindowTitle(window_title)
    msg.exec_()

## Create a subclass of GraphicsObject.
## The only required methods are paint() and boundingRect() 
## (see QGraphicsItem documentation)
class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  ## data must have fields: time, open, close, min, max
        self.generatePicture()
    
    def generatePicture(self):
        ## pre-computing a QPicture object allows paint() to run much more quickly, 
        ## rather than re-drawing the shapes every time.
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen('w'))
        w = (self.data.iloc[1,0] - self.data.iloc[0,0]) / 3.
        for i in range(len(self.data)):
            (t, open, close, min, max,*_) = self.data.iloc[i]
            p.drawLine(QtCore.QPointF(t, min), QtCore.QPointF(t, max))
            if open > close:
                p.setBrush(pg.mkBrush('g'))
            else:
                p.setBrush(pg.mkBrush('r'))
            p.drawRect(QtCore.QRectF(t-w, open, w*2, close-open))
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtCore.QRectF(self.picture.boundingRect())

class MyMainWindow(QMainWindow):
    def __init__(self, parent = None):
        super(MyMainWindow, self).__init__(parent)
        uic.loadUi(os.path.join(script_path,'stock_monitor_app.ui'),self)
        # self.setupUi(self)
        # plt.style.use('ggplot')
        self.widget_terminal.update_name_space('main_gui',self)
        # self.addToolBar(self.mplwidget.navi_toolbar)
        self.setWindowTitle('Chinese Stock Monitor')
        self.pushButton_extract_1.clicked.connect(lambda:self.plot_dapan_profile(code = data_extractor.index_code_map[self.comboBox_index_type.currentText()], start = (datetime.datetime.today()-datetime.timedelta(365*self.spinBox_previous_years.value())).strftime('%Y-%m-%d'), end = datetime.datetime.today().strftime('%Y-%m-%d')))
        self.pushButton_exract_2.clicked.connect(lambda:self.plot_dapan_profile(code = data_extractor.index_code_map[self.comboBox_index_type.currentText()], start = self.lineEdit_begin_date.text(), end = self.lineEdit_end_date.text()))
        self.comboBox_index_type.currentTextChanged.connect(self.extract_selected_index)
        self.pushButton_last_week.clicked.connect(lambda:self.plot_dapan_profile(code = data_extractor.index_code_map[self.comboBox_index_type.currentText()], start = (datetime.datetime.today()-datetime.timedelta(7)).strftime('%Y-%m-%d'), end = datetime.datetime.today().strftime('%Y-%m-%d')))
        self.pushButton_last_month.clicked.connect(lambda:self.plot_dapan_profile(code = data_extractor.index_code_map[self.comboBox_index_type.currentText()], start = (datetime.datetime.today()-datetime.timedelta(30)).strftime('%Y-%m-%d'), end = datetime.datetime.today().strftime('%Y-%m-%d')))
        self.pushButton_last_three_month.clicked.connect(lambda:self.plot_dapan_profile(code = data_extractor.index_code_map[self.comboBox_index_type.currentText()], start = (datetime.datetime.today()-datetime.timedelta(90)).strftime('%Y-%m-%d'), end = datetime.datetime.today().strftime('%Y-%m-%d')))
        self.pushButton_last_six_month.clicked.connect(lambda:self.plot_dapan_profile(code = data_extractor.index_code_map[self.comboBox_index_type.currentText()], start = (datetime.datetime.today()-datetime.timedelta(183)).strftime('%Y-%m-%d'), end = datetime.datetime.today().strftime('%Y-%m-%d')))
        self.pushButton_last_year.clicked.connect(lambda:self.plot_dapan_profile(code = data_extractor.index_code_map[self.comboBox_index_type.currentText()], start = (datetime.datetime.today()-datetime.timedelta(365)).strftime('%Y-%m-%d'), end = datetime.datetime.today().strftime('%Y-%m-%d')))
        self.pushButton_extract_3.clicked.connect(self.extract_fund_info)
        self.values_000001 = []
        self.values_000016 = []
        self.values_000300 = []
        self.values_000688 = []
        self.values_specified = []
        # self.extract_selected_index()
        self.setup_plot()
        self.data_extractor = data_extractor

    def extract_selected_index(self):
        code = data_extractor.index_code_map[self.comboBox_index_type.currentText()]
        if len(getattr(self,'values_{}'.format(code)))==0:
            setattr(self,'values_{}'.format(code),data_extractor.extract_all_records(code))
        self.set_current_price(code)

    def extract_fund_info(self):
        js = data_extractor.extract_one_fund(code = self.lineEdit_fund_code.text())
        self.lineEdit_fund_name.setText(js.eval('fS_name'))
        self.lineEdit_fund_net_wealth.setText(str(js.eval('Data_netWorthTrend')[-1]['y']))
        self.lineEdit_fund_accumulate_wealth.setText(str(js.eval('Data_ACWorthTrend')[-1][1]))
        change = (js.eval('Data_netWorthTrend')[-1]['y'] - js.eval('Data_netWorthTrend')[-2]['y'])/js.eval('Data_netWorthTrend')[-2]['y']*100
        self.lineEdit_fund_change.setText('{}%'.format(round(change,2)))
        self.lineEdit_fund_total.setText(str(js.eval('Data_fluctuationScale')['series'][-1]['y']))
        net_ = js.eval('Data_netWorthTrend')
        net_values = [each['y'] for each in net_]
        dates = [(pd.to_datetime(each['x'], unit="ms", utc=True).tz_convert('Asia/Shanghai').date()-datetime.date(1, 1, 1)).days for each in net_]
        #self.setup_plot_fund()

        self.mpl_widget_jijing.clear()
        self.ax_fund = self.mpl_widget_jijing.addPlot(clear = True)
        self.ax_fund_zoomin = self.mpl_widget_jijing.addPlot(clear = True)
        self.ax_fund.plot(dates,net_values, clear = True)
        self.ax_fund_zoomin.plot(dates,net_values, clear = True)
        self.lr_fund = pg.LinearRegionItem()
        self.lr_fund.setZValue(-10)
        self.lr_fund.sigRegionChanged.connect(self._updatePlot_fund)
        self.ax_fund_zoomin.sigXRangeChanged.connect(self._updateRegion_fund)
        self.ax_fund.addItem(self.lr_fund)
        self.vLine_fund = pg.InfiniteLine(angle=90, movable=False)
        self.hLine_fund = pg.InfiniteLine(angle=0, movable=False)
        self.ax_fund_zoomin.addItem(self.vLine_fund, ignoreBounds=True)
        self.ax_fund_zoomin.addItem(self.hLine_fund, ignoreBounds=True)
        #self.label = pg.LabelItem(justify='right')
        # self.ax_dapan_zoomin.addItem(self.label)
        self.proxy_fund = pg.SignalProxy(self.ax_fund_zoomin.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_fund)
        ticks = [(each, (datetime.date(1, 1, 1)+datetime.timedelta(each)).strftime('%y-%m-%d')) for each in dates]
        self.ax_fund.getAxis('bottom').setTicks([ticks])
        self.ax_fund_zoomin.getAxis('bottom').setTicks([ticks])


    def setup_plot(self):
        self.lr = pg.LinearRegionItem()
        self.lr.setZValue(-10)
        self.ax_dapan = self.mplwidget_dapan.addPlot(clear = True)
        self.ax_dapan_zoomin = self.mplwidget_dapan.addPlot(clear = True)
        self.lr.sigRegionChanged.connect(self._updatePlot)
        self.ax_dapan_zoomin.sigXRangeChanged.connect(self._updateRegion)
        self.ax_dapan.addItem(self.lr)
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.ax_dapan_zoomin.addItem(self.vLine, ignoreBounds=True)
        self.ax_dapan_zoomin.addItem(self.hLine, ignoreBounds=True)
        self.label = pg.LabelItem(justify='right')
        # self.ax_dapan_zoomin.addItem(self.label)
        self.proxy = pg.SignalProxy(self.ax_dapan_zoomin.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

    def setup_plot_fund(self):
        #fund
        self.mpl_widget_jijing.clear()
        self.lr_fund = pg.LinearRegionItem()
        self.lr_fund.setZValue(-10)
        self.ax_fund = self.mpl_widget_jijing.addPlot(clear = True)
        self.ax_fund_zoomin = self.mpl_widget_jijing.addPlot(clear = True)
        self.lr_fund.sigRegionChanged.connect(self._updatePlot_fund)
        self.ax_fund_zoomin.sigXRangeChanged.connect(self._updateRegion_fund)
        self.ax_fund.addItem(self.lr_fund)
        self.vLine_fund = pg.InfiniteLine(angle=90, movable=False)
        self.hLine_fund = pg.InfiniteLine(angle=0, movable=False)
        self.ax_fund_zoomin.addItem(self.vLine_fund, ignoreBounds=True)
        self.ax_fund_zoomin.addItem(self.hLine_fund, ignoreBounds=True)
        #self.label = pg.LabelItem(justify='right')
        # self.ax_dapan_zoomin.addItem(self.label)
        self.proxy_fund = pg.SignalProxy(self.ax_fund_zoomin.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_fund)

    def set_current_price(self, code):
        if len(getattr(self,'values_{}'.format(code)))==0:
            setattr(self,'values_{}'.format(code),data_extractor.extract_all_records(code))
        self.lineEdit_close_price.setText(str(getattr(self,'values_{}'.format(code))['close_price'].iloc[-1]))
        self.lineEdit_open_price.setText(str(getattr(self,'values_{}'.format(code))['open_price'].iloc[-1]))
        self.lineEdit_high_price.setText(str(getattr(self,'values_{}'.format(code))['high_price'].iloc[-1]))
        self.lineEdit_low_price.setText(str(getattr(self,'values_{}'.format(code))['low_price'].iloc[-1]))
        self.lineEdit_volume.setText(str(getattr(self,'values_{}'.format(code))['total'].iloc[-1]))
        self.lineEdit_amount.setText(str(getattr(self,'values_{}'.format(code))['trancaction'].iloc[-1]))
        self.lineEdit_amp.setText('%'+str(getattr(self,'values_{}'.format(code))['amp'].iloc[-1]))
        close_current_day = getattr(self,'values_{}'.format(code))['close_price'].iloc[-1]
        close_last_day = getattr(self,'values_{}'.format(code))['close_price'].iloc[-2]
        change = str(round((close_current_day - close_last_day)/close_last_day*100,2))
        # print(getattr(self,'values_{}'.format(code))['rate'].iloc[-1])
        self.lineEdit_change_rate.setText('%'+change)
        # self.lineEdit_amp.setText('%'+str(getattr(self,'values_{}'.format(code))['rate'].iloc[-1]))

    def mouseMoved(self,evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.ax_dapan_zoomin.sceneBoundingRect().contains(pos):
            mousePoint = self.ax_dapan_zoomin.vb.mapSceneToView(pos)
            index = int(mousePoint.x())
            x = (self.values_specified['date']-index).apply(abs).values.argmin() 
            results = [self.values_specified[each].iloc[x] for each in ['date','open_price','close_price','high_price','low_price','rate','amp','total','trancaction']]
            results[0] = (datetime.date(1, 1, 1)+datetime.timedelta(int(results[0]))).strftime('%Y-%m-%d')
            self.lineEdit_single_point.setText('开盘日期:{};    开盘价:{};    收盘价:{};    最高值:{};    最低值:{};    涨跌幅:{:4.2f}%;    震幅:{}%;    总市值:{};    成交量:{}'.format(*results))
            # self.label.setText("<span style='font-size: 12pt'>x=%0.1f,   <span style='color: red'>y1=%0.1f</span>,   <span style='color: green'>y2=%0.1f</span>" % (mousePoint.x(), 1, 2))
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def mouseMoved_fund(self,evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.ax_fund_zoomin.sceneBoundingRect().contains(pos):
            mousePoint = self.ax_fund_zoomin.vb.mapSceneToView(pos)
            self.vLine_fund.setPos(mousePoint.x())
            self.hLine_fund.setPos(mousePoint.y())

    def _updatePlot(self):
        self.ax_dapan_zoomin.setXRange(*self.lr.getRegion(), padding=0)

    def _updatePlot_fund(self):
        self.ax_fund_zoomin.setXRange(*self.lr_fund.getRegion(), padding=0)

    def _updateRegion(self):
        self.lr.setRegion(self.ax_dapan_zoomin.getViewBox().viewRange()[0])

    def _updateRegion_fund(self):
        self.lr_fund.setRegion(self.ax_fund_zoomin.getViewBox().viewRange()[0])

    def plot_dapan_profile(self, code = '000001', start = '2019-01-01', end = '2021-03-22'):
        self.mplwidget_dapan.clear()
        self.setup_plot()
        if getattr(self,'values_{}'.format(code)).__len__() == 0:                
            setattr(self,'values_{}'.format(code),data_extractor.extract_all_records(code))
        values = data_extractor.extract_index_data(code, start, end, getattr(self,'values_{}'.format(code)))
        self.values_specified = values
        item = CandlestickItem(values)
        item2 = CandlestickItem(values)
        self.ax_dapan.addItem(item)
        self.ax_dapan_zoomin.addItem(item2)
        ticks = [(each, (datetime.date(1, 1, 1)+datetime.timedelta(each)).strftime('%y-%m-%d')) for each in values['date']]
        self.ax_dapan.getAxis('bottom').setTicks([ticks])
        self.ax_dapan_zoomin.getAxis('bottom').setTicks([ticks])
        # self._updatePlot()


if __name__ == "__main__":
    QApplication.setStyle("windows")
    app = QApplication(sys.argv)
    myWin = MyMainWindow()
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    myWin.show()
    sys.exit(app.exec_())