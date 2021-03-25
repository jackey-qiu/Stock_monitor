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
import ray
import psutil

ray.init(num_cpus = psutil.cpu_count(logical=False))

index_code_map = {'上证指数':'000001','上证50':'000016','沪深300':'000300','科创50':'000688'}
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

def extract_index_data(code, start, end, results = []):
    if len(results)==0:
        results = extract_all_records(code)
    data_in_target = results[(results['date']<=pd.Timestamp(end)) & (results['date']>=pd.Timestamp(start))]
    data_in_target['date'] = data_in_target['date'].apply(lambda x: (x.date()-datetime.date(1, 1, 1)).days)
    return data_in_target[['date','open_price','close_price','low_price','high_price','trancaction','total','rate','amp']]

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
class get_fund_dates():
    def __init__(self):
        self.dates = []
        self.processes = psutil.cpu_count(logical=False)

    def get_url(self, url, params=None, proxies=None):
        rsp = requests.get(url, params=params, proxies=proxies)
        rsp.raise_for_status()
        return rsp.text

    def get_fund_total(self, code,start='', end=''):
        url = 'http://fund.eastmoney.com/f10/F10DataApi.aspx'
        params = {'type': 'lsjz', 'code': code, 'page': 10, 'per': 49, 'sdate': start, 'edate': end}
        html = self.get_url(url, params)
        temp =html.split(',')
        return temp[1].split(':')[1],temp[2].split(':')[1],temp[3].replace("};","").split(':')[1]

    def _make_task_map(self, num_tasks):
        extra_tasks = num_tasks%self.processes
        tasks_even_portion = int(num_tasks/self.processes)
        tasks_list = [tasks_even_portion for i in range(self.processes)]
        for i in range(extra_tasks):
            tasks_list[i] += 1
        tasks_list = np.cumsum([0]+tasks_list)
        task_map = {}
        for i in range(self.processes):
            task_map[i] = [tasks_list[i],tasks_list[i+1]]
        self.task_map = task_map

    def get_fund_data(self, code, start='', end='',p=0):
        #record = {'Code': code}
        url = 'http://fund.eastmoney.com/f10/F10DataApi.aspx'
        params = {'type': 'lsjz', 'code': code, 'page': p+1, 'per': 49, 'sdate': start, 'edate': end}
        html = self.get_url(url, params)
        soup = BeautifulSoup(html, 'html.parser')
        records = []
        tab = soup.findAll('tbody')[0]
        for tr in tab.findAll('tr'):
            if tr.findAll('td') and len((tr.findAll('td'))) == 7:
                records.append(str(tr.select('td:nth-of-type(1)')[0].getText().strip()))
                #record['NetAssetValue'] = str(tr.select('td:nth-of-type(2)')[0].getText().strip())
                #record['ChangePercent'] = str(tr.select('td:nth-of-type(4)')[0].getText().strip())
                #records.append(record.copy())
        return records

    @ray.remote
    def get_fund_data_multi_pages(self, code, start='', end='',ps=[0,1]):
        records = []
        print(ps)
        for p in list(range(ps[0],ps[1])):
            records = records + self.get_fund_data(code, start='', end='',p=p)
        return records

    def get_info_ray(self,code = '005827', start = '2018-09-05', end = None):
        if end == None:
           end = time.strftime("%Y-%m-%d",time.localtime())
        total, pages, currentpage = self.get_fund_total(code, start, end)
        self._make_task_map(int(pages))
        results = [ray.get(self.get_fund_data_multi_pages.remote(code, start, end, self.task_map[i])) for i in range(self.processes)]
        results_flat = []
        for each in results:
            results_flat = results_flat + each
        return results_flat

    def get_info(self, code = '005827', start = '2018-09-05', end = None):
        if end == None:
           end = time.strftime("%Y-%m-%d",time.localtime())
        total, pages, currentpage = self.get_fund_total(code, start, end)
        dates = []
        for i in range(int(pages)):
            records = self.get_fund_data(code, start, end,i)
            dates = dates + records
        self.dates = dates
        return dates
