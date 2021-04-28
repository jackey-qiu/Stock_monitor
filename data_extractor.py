import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import urllib.request as urllib2
import json
import datetime, time
from io import StringIO
import requests
import execjs
from bs4 import BeautifulSoup
#import ray
import psutil
import akshare as ak
import baostock as bs

#ray.init(num_cpus = psutil.cpu_count(logical=False))
pe_name_map = {
            '沪深300市盈率'	:'000300.XSHG',
            '上证50市盈率':	'000016.XSHG',
            '上证180市盈率'	:'000010.XSHG',
            '上证380市盈率'	:'000009.XSHG',
            '中证流通市盈率':'000902.XSHG',
            '中证100市盈率'	:'000903.XSHG',
            '中证500市盈率'	:'000905.XSHG',
            '中证800市盈率'	:'000906.XSHG',
            '中证1000市盈率':'000852.XSHG',
            '上证A股市盈率'	:'sh',
            '深圳A股市盈率'	:'sz',
            '中小板市盈率':	'zx',
            '创业板市盈率':	'cy',
            '科创板市盈率':	'kc',
            '全部A股市盈率':'all'
            }

index_code_map = {'上证指数':'sh000001','上证50':'sh000016','沪深300':'sh000300','科创50':'sh000688'}
index_code_map2 = {'上证指数':'000001','上证50':'000016','沪深300':'000300','科创50':'000688'}
url_template = 'http://push2his.eastmoney.com/api/qt/stock/kline/get?cb=jQuery1124034703156772714716_1606741623783&secid=1.{}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58&klt=101&fqt=0&beg=19900101&end=20220101&_=1606741623987'

def extract_all_records(code):
    Req=urllib2.Request(url_template.format(code))
    Respon=urllib2.urlopen(Req)
    Res = Respon.read().decode()
    Res=Res[Res.find('klines')+8:len(Res)-4]
    Res_json = json.loads(Res)
    results = pd.read_csv(StringIO('\n'.join(Res_json)),names = ['date','open_price','close_price','high_price','low_price','trancaction','total','amp'])
    results['date'] = results['date'].apply(pd.Timestamp)
    results['rate'] = pd.Series([0]).append(pd.Series((results['close_price'].iloc[1:].values-results['close_price'].iloc[0:-1].values)/results['close_price'].iloc[0:-1].values)).values*100
    return results

def extract_index_records(code='sh000016', start=None, end=None):
    #code should start with 'sh' or  'sz'
    result = ak.stock_zh_index_daily(symbol=code)
    result.index = result.index.tz_localize(None)
    result['date'] = result.index
    result = result[['date','open','close','high','low','volume']]
    result['total'] = 'NaN'
    result['amp'] = 'NaN'
    result.columns = ['date','open_price','close_price','high_price','low_price','trancaction','total','amp']
    result['rate'] = pd.Series([0]).append(pd.Series((result['close_price'].iloc[1:].values-result['close_price'].iloc[0:-1].values)/result['close_price'].iloc[0:-1].values)).values*100
    if start==None and end==None:
        data_in_target = result
    else:
        data_in_target = result[(result['date']<=pd.Timestamp(end)) & (result['date']>=pd.Timestamp(start))]
    data_in_target['date'] = data_in_target['date'].apply(lambda x: (x.date()-datetime.date(1, 1, 1)).days)
    data_in_target.index = data_in_target.index.rename('')
    data_in_target = data_in_target.reset_index()
    return data_in_target[['date','open_price','close_price','low_price','high_price','trancaction','total','rate','amp']]

#ak.stock_a_lg_indicator(stock="all")获取股票代码
#identifier = 'a' means A-stock(eg. sh600000), 'hk' means Hongkong-stock(eg 00700), 'us' means US-stock (eg. "AAPL")
def extract_stock_records(code='sh600000', start=None, end =None,adjust = 'qfq', identifier = 'a'):
    #qfq:前复权, hfq:后复权
    if identifier == 'a':
        result = ak.stock_zh_a_daily(symbol=code, adjust=adjust)
    elif identifier == 'hk':
        result = ak.stock_hk_daily(symbol=code, adjust=adjust)
    elif identifier == 'us':
        result = ak.stock_us_daily(symbol=code, adjust=adjust)
    result.index = result.index.tz_localize(None)
    result['date'] = result.index
    result = result[['date','open','close','high','low','volume']]
    result['total'] = 'NaN'
    result['amp'] = 'NaN'
    result.columns = ['date','open_price','close_price','high_price','low_price','trancaction','total','amp']
    result['rate'] = pd.Series([0]).append(pd.Series((result['close_price'].iloc[1:].values-result['close_price'].iloc[0:-1].values)/result['close_price'].iloc[0:-1].values)).values*100
    if start==None and end==None:
        pass
    else:
        result = result[(result['date']<=pd.Timestamp(end)) & (result['date']>=pd.Timestamp(start))]
    result['date'] = result['date'].apply(lambda x: (x.date()-datetime.date(1, 1, 1)).days)
    result.index = result.index.rename('')
    result = result.reset_index()
    return result[['date','open_price','close_price','low_price','high_price','trancaction','total','rate','amp']]

def extract_index_data(code, start, end, results = []):
    if len(results)==0:
        results = extract_all_records(code)
    data_in_target = results[(results['date']<=pd.Timestamp(end)) & (results['date']>=pd.Timestamp(start))]
    data_in_target['date'] = data_in_target['date'].apply(lambda x: (x.date()-datetime.date(1, 1, 1)).days)
    return data_in_target[['date','open_price','close_price','low_price','high_price','trancaction','total','rate','amp']]

#the code is one of the value in the pe_name_map
def extract_index_pe_data(code='000300.XSHG', start=None, end=None, script_path = ''):
    def _convert_date(date_str):
        return (datetime.datetime.strptime(date_str, '%Y-%m-%d').date() - datetime.date(1, 1, 1)).days
    path = os.path.join(script_path, 'pe_data', list(pe_name_map.keys())[list(pe_name_map.values()).index(code)]+'.csv')
    if datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d')!= datetime.datetime.today().strftime('%Y-%m-%d'):
        try:
            data = ak.stock_a_pe(market=code)
            data.to_csv(path)
            print('pe data have been updated successfully!')
        except:
            print('Could not update the pe data from server, use the old data instead!')
    else:
        pass
    data = pd.read_csv(path)
    data['date'] = data['date'].apply(pd.Timestamp)
    if start==None and end==None:
        data_sub = data
    else:
        data_sub = data[(data['date']>=pd.Timestamp(start)) & (data['date']<=pd.Timestamp(end))]
    data_sub['date'] = data_sub['date'].apply(lambda x:x.strftime('%Y-%m-%d'))
    data_sub['date'] = data_sub['date'].apply(_convert_date)
    if 'averagePETTM' in data_sub.columns:
        return data_sub[['date','averagePETTM']]
    else:
        data_sub = data_sub[['date','pe']]
        data_sub.columns = ['date','averagePETTM']
        return data_sub

    '''
    lg = bs.login()
    rs = bs.query_history_k_data("sh."+code,"date,peTTM",start_date=start, end_date=end,frequency="d", adjustflag="3")
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data()) 
    result = pd.DataFrame(data_list, columns=rs.fields)
    '''

    # return result

#[...['000002', 'HXCZHH', '华夏成长混合(后端)', '混合型', 'HUAXIACHENGZHANGHUNHE']...]
def extract_all_fund_codes():
    content = requests.get('http://fund.eastmoney.com/js/fundcode_search.js')
    jsContent = execjs.compile(content.text)
    code = jsContent.eval('r')
    return code

def extract_one_fund(code = '005827'):
    def _getUrl():
        head = 'http://fund.eastmoney.com/pingzhongdata/'
        tail = '.js?v='+ time.strftime("%Y%m%d%H%M%S",time.localtime())
        return head+code+tail
    #用requests获取到对应的文件
    content = requests.get(_getUrl())
    #使用execjs获取到相应的数据
    jsContent = execjs.compile(content.text)
    return jsContent

def extract_multiple_funds(code_list):
    fund_info = {}
    for code in code_list:
        js = extract_one_fund(code)
        #extract net fund wealth
        net_ = js.eval('Data_netWorthTrend')
        net_values = [each['y'] for each in net_]
        dates = [(pd.to_datetime(each['x'], unit="ms", utc=True).tz_convert('Asia/Shanghai').date()-datetime.date(1, 1, 1)).days for each in net_]
        fund_info[code] = {'dates':dates, 'net_wealth':net_values}
    return fund_info

def calc_profit(fund_info, purchase_info, output_date):
    #fund_info = {'000001':{'dates':[736941],'net_wealth':[2.8]}}
    #purchase_info = {'000001':{'buy_in_date':['2021-01-01'], 'sell_out_date':['2021-02-05'],'buy_in_quantity':[10],'sell_out_quantity':[10]}}
    #output_date = '2021-04-01'
    def _later_date(date_str1, date_str2):
        return (datetime.datetime.strptime(date_str1, "%Y-%m-%d").date()-datetime.datetime.strptime(date_str2, "%Y-%m-%d").date()).days>=0
    def _get_price(code, date_str):
        days = (datetime.datetime.strptime(date_str, "%Y-%m-%d").date() - datetime.date(1, 1, 1)).days
        return fund_info[code]['net_wealth'][np.argmin(np.abs(np.array(fund_info[code]['dates'])-days))]

    cost_total = 0
    quantity_in_market = {}
    amount_in_hand = 0
    for each in purchase_info:
        quantity_in_market[each] = 0
        for i, item in enumerate(purchase_info[each]['buy_in_date']):
            if _later_date(output_date, item) and purchase_info[each]['buy_in_quantity'][i]!=0:
                cost_total += purchase_info[each]['buy_in_quantity'][i]*_get_price(each,item)
                quantity_in_market[each] += purchase_info[each]['buy_in_quantity'][i]
        for i, item in enumerate(purchase_info[each]['sell_out_date']):
            if _later_date(output_date, item) and purchase_info[each]['sell_out_quantity'][i]!=0:
                quantity_in_market[each] -= purchase_info[each]['sell_out_quantity'][i]
                amount_in_hand += purchase_info[each]['sell_out_quantity'][i]*_get_price(each,purchase_info[each]['sell_out_date'][i])
    amount_in_market = sum([quantity_in_market[each]*_get_price(each, output_date) for each in quantity_in_market])
    # print(cost_total, amount_in_market, amount_in_hand)
    if cost_total==0:
        return 0, 0, 0
    return round((amount_in_market + amount_in_hand - cost_total)/cost_total*100,2), amount_in_market+amount_in_hand, cost_total
    
'''
get value of each time use: e.g. jsContent.eval('fS_name')
var fS_name = "易方达蓝筹精选混合";
var fS_code = "005827";
/*原费率*/var fund_sourceRate="1.50";
/*现费率*/var fund_Rate="0.15";
/*最小申购金额*/var fund_minsg="10";
/*基金持仓股票代码*/var stockCodes
*同类排名百分比*/var Data_rateInSimilarPersent
/*基金持仓债券代码*/var zqCodes = "";
/*收益率*//*近一年收益率*/var syl_1n="101.34";
/*近6月收益率*/var syl_6y="26.55";
/*近三月收益率*/var syl_3y="1.74";
/*近一月收益率*/var syl_1y="-11.23";
/*股票仓位测算图*/var Data_fundSharesPositions= [[1614096000000,95.00],[1614182400000,86.7500]...]
/*单位净值走势 equityReturn-净值回报 unitMoney-每份派送金*/var Data_netWorthTrend = [{"x":1536076800000,"y":1.0,"equityReturn":0,"unitMoney":""},...]
/*累计净值走势*/var Data_ACWorthTrend = [[1536076800000,1.0],[1536249600000,0.9986]...]
/*累计收益率走势*/var Data_grandTotal = [{"name":"易方达蓝筹精选混合","data":[[1600876800000,0],[1600963200000,-0.15]...}]
/*同类排名走势*/var Data_rateInSimilarType = [{"x":1543939200000,"y":1209,"sc":"2763"},...}
/*同类排名百分比*/var Data_rateInSimilarPersent=[[1543939200000,56.2400],[1544025600000,41.1200],...]
/*规模变动 mom-较上期环比*/var Data_fluctuationScale = {"categories":["2019-12-31","2020-03-31","2020-06-30","2020-09-30","2020-12-31"],"series":[{"y":84.24,"mom":"25.40%"},{"y":93.34,"mom":"10.81%"},{"y":182.19,"mom":"95.19%"},{"y":339.38,"mom":"86.28%"},{"y":677.01,"mom":"99.49%"}]};
/*资产配置*/var Data_assetAllocation = {"series":[{"name":"股票占净比","type":null,"data":[94.54,92.54,94.31,94.09],"yAxis":0},...}
/*业绩评价 ['选股能力', '收益率', '抗风险', '稳定性','择时能力']*/var Data_performanceEvaluation = {"avr":"77.50","categories":["选证能力","收益率","抗风险","稳定性","择时能力"],"dsc":["反映基金挑选证券而实现风险\u003cbr\u003e调整后获得超额收益的能力","根据阶段收益评分，反映基金的盈利能力","反映基金投资收益的回撤情况","反映基金投资收益的波动性","反映基金根据对市场走势的判断，\u003cbr\u003e通过调整仓位及配置而跑赢基金业\u003cbr\u003e绩基准的能力"],"data":[80.0,100.0,50.0,50.0,70.0]};
/*现任基金经理*/var Data_currentFundManager =[{"id":"30189744","pic":"https://pdf.dfcfw.com/pdf/H8_PNG30189744_1.jpg","name":"张坤","star":4,"workTime":"8年又179天","fundSize":"1197.46亿(4只基金)","power":{"avr":"73.45","categories":["经验值","收益率","抗风险","稳定性","择时能力"],"dsc":["反映基金经理从业年限和管理基金的经验","根据基金经理投资的阶段收益评分，反映\u003cbr\u003e基金经理投资的盈利能力","反映基金经理投资的回撤控制能力","反映基金经理投资收益的波动","反映基金经理根据对市场的判断，通过\u003cbr\u003e调整仓位及配置而跑赢业绩的基准能力"],"data":[88.80,96.70,36.70,30.0,79.40],"jzrq":"2021-03-24"},"profit":{"categories":["任期收益","同类平均","沪深300"],"series":[{"data":[{"name":null,"color":"#7cb5ec","y":183.18},{"name":null,"color":"#414c7b","y":72.55},{"name":null,"color":"#f7a35c","y":51.88}]}],"jzrq":"2021-03-24"}}] ;
'''

def extract_porfolio_info(code, year, quarter):
    results = ak.fund_em_portfolio_hold(code=code, year=str(year))
    condition = results['季度'] == '{}年{}季度股票投资明细'.format(year, quarter)
    return results[condition]

def extract_fund_rank(fund_type, sort_by, sort_method):
    fund_em_open_fund_rank_df = ak.fund_em_open_fund_rank(symbol=fund_type)
    for each in sort_by:
        fund_em_open_fund_rank_df[each] = fund_em_open_fund_rank_df[each].replace('',np.nan).astype(float)
    return fund_em_open_fund_rank_df.sort_values(by=sort_by,ascending = sort_method)

def calc_wealth(years = 10, month_saving_amount = 500, month_profit_rate = 0.01):
    total_months = years*12
    total_wealth = 0
    time_list = []
    wealth_list = []
    cost_list = []
    for i in range(total_months):
        time_list.append(i/12.)
        total_wealth += month_saving_amount*(1+month_profit_rate)**(total_months-i)
        total_wealth_this_month = 0
        for ii in range(i+1):
            total_wealth_this_month += month_saving_amount*(1+month_profit_rate)**(i+1-ii)
        wealth_list.append(total_wealth_this_month)
        cost_list.append((i+1)*month_saving_amount)
    
    # print('Total wealth is {} after {} years with a saving plan at monthly raising rate of {} and monthly saving amount of {}'.format(total_wealth, years, month_profit_rate, month_saving_amount))
    # print('Net profit is {} at a investment rate of {}%'.format(total_wealth-month_saving_amount*total_months, total_wealth/(month_saving_amount*total_months)*100))
    return time_list, cost_list, wealth_list

def calc_wealth_once_investment(years = 10, total_invest_amount = 1000000, month_profit_rate = 0.01):
    total_months = years*12
    time_list = []
    wealth_list = []
    cost_list = []
    total_wealth = total_invest_amount*(1+month_profit_rate)**total_months
    for i in range(total_months):
        time_list.append(i/12.)
        cost_list.append(total_invest_amount)
        wealth_list.append(total_invest_amount*(1+month_profit_rate)**(i+1))
    # print('Total wealth is {} after {} years with an one-time investment of {} at monthly raising rate of {} '.format(total_wealth, years, total_invest_amount, month_profit_rate))
    # print('Net profit is {} at a investment rate of {}%'.format(total_wealth-total_invest_amount, (total_wealth-total_invest_amount)/total_invest_amount*100))
    return time_list, cost_list, wealth_list

