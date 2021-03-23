import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import urllib.request as urllib2
import json
import datetime
from io import StringIO

index_code_map = {'上证指数':'000001','上证50':'000016','沪深300':'000300','科创50':'000688'}
url_template = 'http://push2his.eastmoney.com/api/qt/stock/kline/get?cb=jQuery1124034703156772714716_1606741623783&secid=1.{}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58&klt=101&fqt=0&beg=19900101&end=20220101&_=1606741623987'

def extract_all_records(code):
    Req=urllib2.Request(url_template.format(code))
    Respon=urllib2.urlopen(Req)
    Res = Respon.read().decode()
    Res=Res[Res.find('klines')+8:len(Res)-4]
    Res_json = json.loads(Res)
    results = pd.read_csv(StringIO('\n'.join(Res_json)),names = ['date','open_price','close_price','high_price','low_price','trancaction','total','rate'])
    results['date'] = results['date'].apply(pd.Timestamp)
    return results

def extract_index_data(code, start, end, results = []):
    if len(results)==0:
        results = extract_all_records(code)
    data_in_target = results[(results['date']<=pd.Timestamp(end)) & (results['date']>=pd.Timestamp(start))]
    data_in_target['date'] = data_in_target['date'].apply(lambda x: (x.date()-datetime.date(1, 1, 1)).days)
    #dates_in_target = []
    '''
    start = datetime.datetime.strptime(start,'%Y-%m-%d')
    end = datetime.datetime.strptime(end,'%Y-%m-%d')
    date_0001_01_01 = datetime.date(1, 1, 1)
    hit = False
    for each in Res_json:
        temp_date = each[0:10]
        date = datetime.datetime.strptime(temp_date,'%Y-%m-%d')
        if end >= date >= start:
            if not hit:
                hit = True
            #dates_in_target.append(temp_date)
            values_ = eval('[{}]'.format(each[11:]))
            # values = [float((date.date()-date_0001_01_01).days), values_[0],values_[2], values_[3], values_[1]]
            values = [float((date.date()-date_0001_01_01).days)] + values_[0:4]
            data_in_target.append(values)
        else:
            if hit:
                break
            else:
                pass
    '''
    return data_in_target[['date','open_price','close_price','low_price','high_price','trancaction','total','rate']]
        

    


