import sys,os,qdarkstyle
import urllib
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QInputDialog, QMessageBox
from PyQt5.QtGui import QPixmap, QImage
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
from PyQt5 import uic, QtCore
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

class PandasModel(QtCore.QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    """
    def __init__(self, data, tableviewer, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._data = data
        self.tableviewer = tableviewer

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role):
        if index.isValid():
            if role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole] and index.column()!=0:
                return str(self._data.iloc[index.row(), index.column()])
            if role == QtCore.Qt.BackgroundRole and index.row()%2 == 0:
                return QtGui.QColor('lightGray')
            if role == QtCore.Qt.BackgroundRole and index.row()%2 == 1:
                return QtGui.QColor('cyan')
            if role == QtCore.Qt.CheckStateRole and index.column()==0:
                if self._data.iloc[index.row(),index.column()]:
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked
        return None

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            if value == QtCore.Qt.Checked:
                self._data.iloc[index.row(),index.column()] = True
            else:
                self._data.iloc[index.row(),index.column()] = False
        else:
            if str(value)!='':
                self._data.iloc[index.row(),index.column()] = str(value)
        self.dataChanged.emit(index, index)
        self.layoutAboutToBeChanged.emit()
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
        self.layoutChanged.emit()
        self.tableviewer.resizeColumnsToContents() 
        return True

    def update_view(self):
        self.layoutAboutToBeChanged.emit()
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(self.rowCount(0), self.columnCount(0)))
        self.layoutChanged.emit()

    def headerData(self, rowcol, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._data.columns[rowcol]         
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return self._data.index[rowcol]         
        return None

    def flags(self, index):
        if not index.isValid():
           return QtCore.Qt.NoItemFlags
        else:
            if index.column()==0:
                return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable)
            else:
                return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)

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
        self.pushButton_add_to_fund_group.clicked.connect(self.add_to_fund_group)
        self.pushButton_cal_group_profit.clicked.connect(self.calc_profit)
        self.pushButton_add_one_row.clicked.connect(self.append_one_row)
        self.pushButton_save_fund_group.clicked.connect(self.save_fund_group)
        self.comboBox_fund_group_list.activated.connect(self.load_fund_group)
        self.values_000001 = []
        self.values_000016 = []
        self.values_000300 = []
        self.values_000688 = []
        self.values_specified = []
        # self.extract_selected_index()
        self.setup_plot()
        self.data_extractor = data_extractor
        self.fill_fund_groups()

    def fill_fund_groups(self):
        self.comboBox_fund_group_list.clear()
        items = os.listdir(os.path.join(script_path,'fund_group'))
        self.comboBox_fund_group_list.addItems(items)

    def load_fund_group(self):
        path = os.path.join(script_path, 'fund_group', self.comboBox_fund_group_list.currentText())
        data = pd.read_csv(path,dtype = str)
        data['选择'] = data['选择'].astype(bool)
        if not hasattr(self, 'pandas_model_fund_group'):
            self.pandas_model_fund_group = PandasModel(data = data,tableviewer = self.tableView_fund_group_list, parent=self) 
            self.tableView_fund_group_list.setModel(self.pandas_model_fund_group)
            self.tableView_fund_group_list.resizeColumnsToContents() 
        else:
            self.pandas_model_fund_group._data = data
        self.pandas_model_fund_group.update_view()

    def save_fund_group(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存基金组合", "", "csv file (*.csv);;")
        if path:
            self.pandas_model_fund_group._data.to_csv(path,index=False)
            self.statusbar.clearMessage()
            self.statusbar.showMessage('Success to save fund group!')
            self.fill_fund_groups()

    def add_to_fund_group(self):
        df_selected_fund_groups = self.pandas_model._data[self.pandas_model._data['选择']][['选择','基金代码','基金简称','日期','单位净值']]
        df_selected_fund_groups['购入日期'] = str([self.pandas_model._data['日期'][0]])
        df_selected_fund_groups['购入数量'] = str([0])
        df_selected_fund_groups['卖出日期'] = str([self.pandas_model._data['日期'][0]])
        df_selected_fund_groups['卖出数量'] = str([0])
        self.pandas_model_fund_group = PandasModel(data=df_selected_fund_groups,tableviewer = self.tableView_fund_group_list, parent=self)
        self.tableView_fund_group_list.setModel(self.pandas_model_fund_group)
        self.tableView_fund_group_list.resizeColumnsToContents() 

    def append_one_row(self):
        code, done = QInputDialog.getText(self, '追加一行', '基金代码:')
        if done:
            # append_row = self.pandas_model._data[self.pandas_model._data['基金代码']==code][['选择','基金代码','基金简称','日期','单位净值']]
            append_row = self.results_fund_rank[self.results_fund_rank['基金代码']==code][['基金代码','基金简称','日期','单位净值']]
            append_row['购入日期'] = str([self.pandas_model._data['日期'][0]])
            append_row['购入数量'] = str([0])
            append_row['卖出日期'] = str([self.pandas_model._data['日期'][0]])
            append_row['卖出数量'] = str([0])
            append_row.insert(0,column = '选择', value = True)
            self.pandas_model_fund_group._data = pd.concat([self.pandas_model_fund_group._data,append_row])
            self.pandas_model_fund_group.update_view()

    def calc_profit(self):
        def _to_days(date_str):
            return (datetime.datetime.strptime(date_str, "%Y-%m-%d").date() - datetime.date(1, 1, 1)).days

        def _extract_purchase_dates(purchase_info):
            buy_in_dates = []
            sell_out_dates = []
            for each in purchase_info:
                for i, item in enumerate(purchase_info[each]['buy_in_date']):
                    if purchase_info[each]['buy_in_quantity'][i]!=0:
                        buy_in_dates.append(_to_days(item))
                for i, item in enumerate(purchase_info[each]['sell_out_date']):
                    if purchase_info[each]['sell_out_quantity'][i]!=0:
                        sell_out_dates.append(_to_days(item))
            return buy_in_dates, sell_out_dates
            
        profits = []
        purchase_info = {}
        date_start = datetime.date.today()
        date_end = datetime.date.today()
        fund_info = data_extractor.extract_multiple_funds(self.pandas_model_fund_group._data['基金代码'].tolist())
        for i in range(len(self.pandas_model_fund_group._data)):
            if self.pandas_model_fund_group._data.iloc[i]['选择']:
                temp_dates = eval(self.pandas_model_fund_group._data.iloc[i]['购入日期'])
                temp_dates.sort(key=lambda date: datetime.datetime.strptime(date, "%Y-%m-%d"))
                temp_date = datetime.datetime.strptime(temp_dates[0], "%Y-%m-%d").date()
                if (temp_date-date_start).days<0:
                    date_start = temp_date
                purchase_info[self.pandas_model_fund_group._data.iloc[i]['基金代码']] = \
                    {
                    'buy_in_date':eval(self.pandas_model_fund_group._data.iloc[i]['购入日期']), 
                    'sell_out_date':eval(self.pandas_model_fund_group._data.iloc[i]['卖出日期']),
                    'buy_in_quantity':eval(self.pandas_model_fund_group._data.iloc[i]['购入数量']),
                    'sell_out_quantity':eval(self.pandas_model_fund_group._data.iloc[i]['卖出数量'])
                    }
        
        interval_days = (date_end-date_start).days
        output_dates = [(date_start + datetime.timedelta(days = i)).strftime('%Y-%m-%d') for i in range(1,interval_days)]
        return_dates = [(date_start + datetime.timedelta(days = i)-datetime.date(1, 1, 1)).days for i in range(1,interval_days)]
        for output_date in output_dates:
            profits.append(data_extractor.calc_profit(fund_info, purchase_info, output_date))
        self.profit_dates = return_dates
        self.profits = profits
        buy_in_dates, sell_out_dates = _extract_purchase_dates(purchase_info)
        #plot the results
        self.widget_profit_curve.clear()
        self.ax_profit = self.widget_profit_curve.addPlot(clear = True)
        self.proxy_profit_investment = pg.SignalProxy(self.ax_profit.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved_profit_investment)
        self.ax_profit.plot(return_dates,profits, clear = True,pen=pg.mkPen('g', width=3))
        self.profits_buy_in = [profits[0]]
        self.profits_sell_out = []
        self.buy_in_dates, self.sell_out_dates = [return_dates[0]], []
        for each in buy_in_dates:
            if each in return_dates:
                self.profits_buy_in.append(profits[return_dates.index(each)])
                self.buy_in_dates.append(each)
        for each in sell_out_dates:
            if each in return_dates:
                self.profits_sell_out.append(profits[return_dates.index(each)])
                self.sell_out_dates.append(each)
        self.ax_profit.addLegend()
        self.ax_profit.plot(self.buy_in_dates, self.profits_buy_in, pen=None, symbolBrush=(200,0,0), symbolPen='w', symbol='o', symbolSize=10, name = '买入')
        self.ax_profit.plot(self.sell_out_dates, self.profits_sell_out, pen=None, symbolBrush=(0, 0,200), symbolPen='w', symbol='o', symbolSize=10, name = '卖出')
        self.set_tick_strings_general(dates = self.profit_dates, ax_handles = [self.ax_profit.getAxis('bottom')], ticks_num = 6)
        self.ax_profit.sigXRangeChanged.connect(lambda:self.set_tick_strings_general(dates = self.profit_dates, ax_handles = [self.ax_profit.getAxis('bottom')], ticks_num = 6))
        self.ax_profit.getAxis('left').setLabel('收益率(%)')
        self.ax_profit.getAxis('bottom').setLabel('日期（年-月-日）')
        self.vLine_profit_investment = pg.InfiniteLine(angle=90, movable=False)
        self.hLine_profit_investment = pg.InfiniteLine(angle=0, movable=False)
        self.ax_profit.addItem(self.vLine_profit_investment, ignoreBounds = True)
        self.ax_profit.addItem(self.hLine_profit_investment, ignoreBounds = True)

        # return return_dates, profits

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
        # self.textBrowser_fund_sorted_results.setHtml(results.iloc[0:num_items].to_html())
        to_be_shown_df = results.iloc[0:num_items]
        to_be_shown_df['选择'] = False
        columns = ['选择'] + to_be_shown_df.columns.tolist()[2:-1]
        self.pandas_model = PandasModel(data=to_be_shown_df[columns],tableviewer = self.tableView_fund_sorted_results, parent=self)
        self.tableView_fund_sorted_results.setModel(self.pandas_model)
        self.tableView_fund_sorted_results.resizeColumnsToContents() 
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

    def mouseMoved_profit_investment(self,evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.ax_profit.sceneBoundingRect().contains(pos):
            mousePoint = self.ax_profit.vb.mapSceneToView(pos)
            index = int(mousePoint.x())
            which = np.argmin(abs(np.array(self.profit_dates)-index))
            result = self.profits[which]
            self.lineEdit_profit_investment.setText('日期:{};  盈亏率:{:4.2f}%;'.format((datetime.date(1, 1, 1)+datetime.timedelta(int(self.profit_dates[which]))).strftime('%Y-%m-%d'),result))
            self.vLine_profit_investment.setPos(mousePoint.x())
            self.hLine_profit_investment.setPos(mousePoint.y())

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