import sys,os,qdarkstyle
import urllib
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt5.QtGui import QPixmap, QImage
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
        #w = (self.data.iloc[1,0] - self.data.iloc[0,0]) / 4.
        w = 1/4.
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
        self.pushButton_extract_4.clicked.connect(self.plot_poforlio_fund)
        self.pushButton_sort_fund.clicked.connect(self.sort_fund_rank)
        self.pushButton_extract_5.clicked.connect(self.get_fund_rank)
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
        self.lineEdit_fund_total.setText(str(js.eval('Data_fluctuationScale')['series'][-1]['y'])+'亿')
        self.lineEdit_profit_one_month.setText(str(js.eval('syl_1y'))+'%')
        self.lineEdit_profit_three_month.setText(str(js.eval('syl_3y'))+'%')
        self.lineEdit_profit_half_year.setText(str(js.eval('syl_6y'))+'%')
        self.lineEdit_profit_one_year.setText(str(js.eval('syl_1n'))+'%')
        self.lineEdit_avg.setText(str(js.eval('Data_performanceEvaluation')['avr']))
        data_ = js.eval('Data_performanceEvaluation')['data']
        lineEdits = [getattr(self, each) for each in ['lineEdit_select_stock','lineEdit_profit','lineEdit_risk_resistance','lineEdit_stability','lineEdit_timing']]
        for i, each in enumerate(lineEdits):
            each.setText(str(data_[i]))
        #fund manager information
        manager_info = js.eval('Data_currentFundManager')[0]
        self.lineEdit_fund_manager_name.setText(manager_info['name'])
        self.lineEdit_fund_manager_star.setText(str(manager_info['star']))
        self.lineEdit_fund_manager_work_years.setText(manager_info['workTime'])
        self.lineEdit_fund_manager_fund_size.setText(manager_info['fundSize'])
        lineEdits_manager = [getattr(self, 'lineEdit_fund_manager_'+each) for each in ['experience','profit','risk_resistance','stability','timing']]
        data_manager = manager_info['power']['data']
        for i, each in enumerate(lineEdits_manager):
            each.setText(str(data_manager[i]))
        self.lineEdit_fund_manager_average.setText(manager_info['power']['avr'])
        #download photo
        f = open(os.path.join(script_path,'temp','manager_photo.jpg'),'wb')           
        f.write(urllib.request.urlopen(manager_info['pic']).read())
        f.close()
        # create QImage from image
        # show image in img_label
        self.label_manager.setPixmap(QPixmap(os.path.join(script_path,'temp','manager_photo.jpg')))
        self.label_manager.setScaledContents(True)
        #extract net fund wealth
        net_ = js.eval('Data_netWorthTrend')
        net_values = [each['y'] for each in net_]
        dates = [(pd.to_datetime(each['x'], unit="ms", utc=True).tz_convert('Asia/Shanghai').date()-datetime.date(1, 1, 1)).days for each in net_]
        self.dates_fund = dates
        self.net_values_fund = net_values
        self.mpl_widget_jijing.clear()
        self.ax_fund = self.mpl_widget_jijing.addPlot(clear = True)
        self.ax_fund_zoomin = self.mpl_widget_jijing.addPlot(clear = True)
        self.ax_fund.plot(dates,net_values, clear = True,pen=pg.mkPen('g', width=3))
        self.ax_fund_zoomin.plot(dates,net_values, clear = True,pen=pg.mkPen('r', width=3))
        self.lr_fund = pg.LinearRegionItem(bounds=[min(dates),max(dates)])
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
        # self.lr_fund.setBounds()
        self.proxy_fund = pg.SignalProxy(self.ax_fund_zoomin.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_fund)
        self.set_tick_strings_fund(dates)
        self.ax_fund.sigXRangeChanged.connect(lambda:self.set_tick_strings_fund(self.dates_fund))
        self.ax_fund_zoomin.sigXRangeChanged.connect(lambda:self.set_tick_strings_fund(self.dates_fund))
        #extract rank among funds of similar type
        rank = js.eval('Data_rateInSimilarPersent')
        self.percent_rank_fund = [each[1] for each in rank]
        self.dates_rank_fund = [(pd.to_datetime(each[0], unit="ms", utc=True).tz_convert('Asia/Shanghai').date()-datetime.date(1, 1, 1)).days for each in rank]
        self.widget_rank.clear()
        self.ax_rank_fund = self.widget_rank.addPlot(clear = True)
        self.ax_rank_fund.getAxis('left').setLabel('排名百分比(%)')
        self.ax_rank_fund.plot(self.dates_rank_fund,self.percent_rank_fund, clear = True, pen=pg.mkPen('w', width=3))
        self.vLine_rank_fund = pg.InfiniteLine(angle=90, movable=False)
        self.hLine_rank_fund = pg.InfiniteLine(angle=0, movable=False)
        self.ax_rank_fund.addItem(self.vLine_rank_fund, ignoreBounds = True)
        self.ax_rank_fund.addItem(self.hLine_rank_fund, ignoreBounds = True)
        self.proxy_rank_fund = pg.SignalProxy(self.ax_rank_fund.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_rank_fund)
        self.set_tick_strings_general(dates = self.dates_rank_fund, ax_handles = [self.ax_rank_fund.getAxis('bottom')], ticks_num = 6)
        self.ax_rank_fund.sigXRangeChanged.connect(lambda:self.set_tick_strings_general(dates = self.dates_rank_fund, ax_handles = [self.ax_rank_fund.getAxis('bottom')], ticks_num = 6))
        #extract grandTotal
        grand = js.eval('Data_grandTotal')
        self.dates_current_fund = [(pd.to_datetime(each[0], unit="ms", utc=True).tz_convert('Asia/Shanghai').date()-datetime.date(1, 1, 1)).days for each in grand[0]['data']]
        self.dates_similar_fund = [(pd.to_datetime(each[0], unit="ms", utc=True).tz_convert('Asia/Shanghai').date()-datetime.date(1, 1, 1)).days for each in grand[1]['data']]
        self.dates_index = [(pd.to_datetime(each[0], unit="ms", utc=True).tz_convert('Asia/Shanghai').date()-datetime.date(1, 1, 1)).days for each in grand[2]['data']]
        self.profit_change_current_fund = [each[1] for each in grand[0]['data']]
        self.profit_change_similar_fund = [each[1] for each in grand[1]['data']]
        self.profit_change_index = [each[1] for each in grand[2]['data']]
        self.widget_profit.clear()
        self.ax_profit_grand = self.widget_profit.addPlot(clear = True)
        self.ax_profit_grand.getAxis('left').setLabel('涨幅率(%)')
        self.ax_profit_grand.addLegend()
        self.ax_profit_grand.plot(self.dates_current_fund,self.profit_change_current_fund, clear = True, pen=pg.mkPen('g', width=2),name = self.lineEdit_fund_name.text())
        self.ax_profit_grand.plot(self.dates_similar_fund,self.profit_change_similar_fund, clear = False, pen=pg.mkPen('r', width=2), name = '同类基金')
        self.ax_profit_grand.plot(self.dates_index,self.profit_change_index, clear = False, pen=pg.mkPen('w', width=2), name = '沪深300')
        self.vLine_profit = pg.InfiniteLine(angle=90, movable=False)
        self.hLine_profit = pg.InfiniteLine(angle=0, movable=False)
        self.ax_profit_grand.addItem(self.vLine_profit, ignoreBounds = True)
        self.ax_profit_grand.addItem(self.hLine_profit, ignoreBounds = True)
        self.proxy_profit = pg.SignalProxy(self.ax_profit_grand.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_profit)
        self.set_tick_strings_general(dates = self.dates_current_fund, ax_handles = [self.ax_profit_grand.getAxis('bottom')], ticks_num = 6)
        self.ax_profit_grand.sigXRangeChanged.connect(lambda:self.set_tick_strings_general(dates = self.dates_current_fund, ax_handles = [self.ax_profit_grand.getAxis('bottom')], ticks_num = 6))

    def plot_poforlio_fund(self):
        self.widget_portfolio_bar.clear()
        year = self.lineEdit_year.text()
        code = self.lineEdit_fund_code.text()
        quarter = self.comboBox_quarter.currentText()
        results_df = data_extractor.extract_porfolio_info(code, year, quarter)
        stock_names = list(results_df['股票名称'])
        percents = list(results_df['占净值比例'].apply(float))
        self.lineEdit_sum.setText('{}%'.format(round(sum(percents[0:10]),2)))
        self.textBrowser_portfolio_list.setHtml(results_df.to_html(index=False))
        # self.textBrowser_portfolio_list.setPlainText(results_df.to_string(col_space = 20,index=False).replace('\n','\n\n'))
        bg1 = pg.BarGraphItem(x=list(range(1,len(percents)+1)), height=percents, width=0.3, brush='g')
        self.ax_bar_fund = self.widget_portfolio_bar.addPlot(clear = True)
        self.ax_bar_fund.addItem(bg1)
        self.ax_bar_fund.getAxis('bottom').setTicks([list(zip(list(range(1,len(percents)+1)),[str(each) for each in range(1,len(percents)+1)]))])
        self.ax_bar_fund.getAxis('bottom').setLabel('序号')
        self.ax_bar_fund.getAxis('left').setLabel('占净值百分比(%)')

    def sort_fund_rank(self):
        fund_type, num_items = self.comboBox_fund_type.currentText(),int(self.spinBox_item_number.value())
        sort_by = []
        sort_method = []
        for i in range(1,4):
            text = getattr(self,'comboBox_sort_key{}'.format(i)).currentText()
            if text != '无':
                sort_by.append(text)
                sort_method.append(getattr(self,'comboBox_sort_method{}'.format(i)).currentText()=='升序')
        results = data_extractor.extract_fund_rank(fund_type,sort_by,sort_method)
        results = results.reset_index()
        self.results_fund_rank = results
        self.textBrowser_fund_sorted_results.setHtml(results.iloc[0:num_items].to_html())
        # self.textBrowser_fund_sorted_results.setPlainText(results.to_string(col_space = 10).replace('\n','\n\n'))

    def get_fund_rank(self):
        rank = self.results_fund_rank['基金代码'][self.results_fund_rank['基金代码']==self.lineEdit_fund_code_2.text()].index.values
        if len(rank)!=0:
            self.lineEdit_rank.setText(str(rank[0])+'/{}'.format(len(self.results_fund_rank)))
        else:
            self.lineEdit_rank.setText('Out of size!')

    def setup_plot(self):
        self.mplwidget_dapan.clear()
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
        self.ax_dapan.sigXRangeChanged.connect(self.set_tick_strings_dapan)
        self.ax_dapan_zoomin.sigXRangeChanged.connect(self.set_tick_strings_dapan)

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
            index = int(mousePoint.x())
            which = np.argmin(abs(np.array(self.dates_fund)-index))
            results = [self.dates_fund[which],self.net_values_fund[which]]
            change = 0
            if which!=0:
                change = (self.net_values_fund[which] - self.net_values_fund[which-1])/self.net_values_fund[which-1]*100
            self.lineEdit_single_point_fund.setText('开盘日期:{};    基金净值:{};    涨跌幅:{:4.2f}%;'.format((datetime.date(1, 1, 1)+datetime.timedelta(int(self.dates_fund[which]))).strftime('%Y-%m-%d'),self.net_values_fund[which],change))
            self.vLine_fund.setPos(mousePoint.x())
            self.hLine_fund.setPos(mousePoint.y())

    def mouseMoved_rank_fund(self,evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.ax_rank_fund.sceneBoundingRect().contains(pos):
            mousePoint = self.ax_rank_fund.vb.mapSceneToView(pos)
            index = int(mousePoint.x())
            which = np.argmin(abs(np.array(self.dates_current_fund)-index))
            result = self.percent_rank_fund[which]
            self.lineEdit_single_point_rank.setText('日期:{};   同类排名百分比:{:4.2f}%;'.format((datetime.date(1, 1, 1)+datetime.timedelta(int(self.dates_rank_fund[which]))).strftime('%Y-%m-%d'),result))
            self.vLine_rank_fund.setPos(mousePoint.x())
            self.hLine_rank_fund.setPos(mousePoint.y())

    def mouseMoved_profit(self,evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.ax_profit_grand.sceneBoundingRect().contains(pos):
            mousePoint = self.ax_profit_grand.vb.mapSceneToView(pos)
            index = int(mousePoint.x())
            which = np.argmin(abs(np.array(self.dates_current_fund)-index))
            result_current_fund = self.profit_change_current_fund[which]
            result_similar_fund = self.profit_change_similar_fund[which]
            result_index = self.profit_change_index[which]
            self.lineEdit_single_point_profit.setText('日期:{};   所选基金:{:4.2f}%;    同类基金:{:4.2f}%;      沪深300:{:4.2f}%;'.format((datetime.date(1, 1, 1)+datetime.timedelta(int(self.dates_current_fund[which]))).strftime('%Y-%m-%d'),result_current_fund,result_similar_fund,result_index))
            self.vLine_profit.setPos(mousePoint.x())
            self.hLine_profit.setPos(mousePoint.y())

    def _updatePlot(self):
        self.ax_dapan_zoomin.setXRange(*self.lr.getRegion(), padding=0)
        bound_left, bound_right = self.lr.getRegion()
        index_left = np.argmin(abs(np.array(self.values_specified['date'])-bound_left))
        index_right = np.argmin(abs(np.array(self.values_specified['date'])-bound_right))
        min_y = min(self.values_specified['low_price'][index_left:index_right])
        max_y = max(self.values_specified['high_price'][index_left:index_right])
        self.ax_dapan_zoomin.setYRange(min_y,max_y, padding=0)


    def _updatePlot_fund(self):
        self.ax_fund_zoomin.setXRange(*self.lr_fund.getRegion(), padding=0)
        bound_left, bound_right = self.lr_fund.getRegion()
        index_left = np.argmin(abs(np.array(self.dates_fund)-bound_left))
        index_right = np.argmin(abs(np.array(self.dates_fund)-bound_right))
        min_y = min(self.net_values_fund[index_left:index_right])
        max_y = max(self.net_values_fund[index_left:index_right])
        self.ax_fund_zoomin.setYRange(min_y,max_y, padding=0)

    def _updateRegion(self):
        self.lr.setRegion(self.ax_dapan_zoomin.getViewBox().viewRange()[0])

    def _updateRegion_fund(self):
        self.lr_fund.setRegion(self.ax_fund_zoomin.getViewBox().viewRange()[0])

    def plot_dapan_profile(self, code = '000001', start = '2019-01-01', end = '2021-03-22'):
        self.setup_plot()
        if getattr(self,'values_{}'.format(code)).__len__() == 0:                
            setattr(self,'values_{}'.format(code),data_extractor.extract_all_records(code))
            self.set_current_price(code)
        values = data_extractor.extract_index_data(code, start, end, getattr(self,'values_{}'.format(code)))
        self.values_specified = values
        item = CandlestickItem(values)
        item2 = CandlestickItem(values)
        self.ax_dapan.addItem(item)
        self.ax_dapan_zoomin.addItem(item2)
        self.set_tick_strings_dapan()

    def set_tick_strings_dapan(self):
        def _find_nearest_neighbor(values_pool, values):
            values_return = []
            values_pool = np.array(values_pool)
            for each in values:
                values_return.append(int(values_pool[np.argmin(abs(values_pool - each))]))
            return list(set(values_return))

        ticks_num = 6
        range_dapan = self.ax_dapan.getAxis('bottom').range
        range_dapan_zoomin = self.ax_dapan_zoomin.getAxis('bottom').range
        dates_raw_dapan = [range_dapan[0] + (range_dapan[1] - range_dapan[0])/ticks_num*i for i in range(ticks_num)]
        dates_raw_dapan_zoomin = [range_dapan_zoomin[0] + (range_dapan_zoomin[1] - range_dapan_zoomin[0])/ticks_num*i for i in range(ticks_num)]
        dates_final_dapan = _find_nearest_neighbor(self.values_specified['date'],dates_raw_dapan)
        dates_final_dapan_zoomin = _find_nearest_neighbor(self.values_specified['date'],dates_raw_dapan_zoomin)
        # print(dates_raw_dapan)
        # print(dates_final_dapan)
        
        ticks_dapan = [(each, (datetime.date(1, 1, 1)+datetime.timedelta(each)).strftime('%y-%m-%d')) for each in dates_final_dapan]
        ticks_dapan_zoomin = [(each, (datetime.date(1, 1, 1)+datetime.timedelta(each)).strftime('%y-%m-%d')) for each in dates_final_dapan_zoomin]
        self.ax_dapan.getAxis('bottom').setTicks([ticks_dapan])
        self.ax_dapan_zoomin.getAxis('bottom').setTicks([ticks_dapan_zoomin])

    def set_tick_strings_general(self, dates, ax_handles, ticks_num = 6):
        def _find_nearest_neighbor(values_pool, values):
            values_return = []
            values_pool = np.array(values_pool)
            for each in values:
                values_return.append(int(values_pool[np.argmin(abs(values_pool - each))]))
            return list(set(values_return))

        for ax_handle in ax_handles:
            range_fund = ax_handle.range
            dates_raw_fund = [range_fund[0] + (range_fund[1] - range_fund[0])/ticks_num*i for i in range(ticks_num)]
            dates_final_fund = _find_nearest_neighbor(dates,dates_raw_fund)
            ticks_fund = [(each, (datetime.date(1, 1, 1)+datetime.timedelta(each)).strftime('%y-%m-%d')) for each in dates_final_fund]
            ax_handle.setTicks([ticks_fund])

    def set_tick_strings_fund(self, dates):
        def _find_nearest_neighbor(values_pool, values):
            values_return = []
            values_pool = np.array(values_pool)
            for each in values:
                values_return.append(int(values_pool[np.argmin(abs(values_pool - each))]))
            return list(set(values_return))

        ticks_num = 6
        range_fund = self.ax_fund.getAxis('bottom').range
        range_fund_zoomin = self.ax_fund_zoomin.getAxis('bottom').range
        dates_raw_fund = [range_fund[0] + (range_fund[1] - range_fund[0])/ticks_num*i for i in range(ticks_num)]
        dates_raw_fund_zoomin = [range_fund_zoomin[0] + (range_fund_zoomin[1] - range_fund_zoomin[0])/ticks_num*i for i in range(ticks_num)]
        dates_final_fund = _find_nearest_neighbor(dates,dates_raw_fund)
        dates_final_fund_zoomin = _find_nearest_neighbor(dates,dates_raw_fund_zoomin)
        ticks_fund = [(each, (datetime.date(1, 1, 1)+datetime.timedelta(each)).strftime('%y-%m-%d')) for each in dates_final_fund]
        ticks_fund_zoomin = [(each, (datetime.date(1, 1, 1)+datetime.timedelta(each)).strftime('%y-%m-%d')) for each in dates_final_fund_zoomin]
        self.ax_fund.getAxis('bottom').setTicks([ticks_fund])
        self.ax_fund_zoomin.getAxis('bottom').setTicks([ticks_fund_zoomin])



if __name__ == "__main__":
    QApplication.setStyle("windows")
    app = QApplication(sys.argv)
    myWin = MyMainWindow()
    # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    myWin.show()
    sys.exit(app.exec_())