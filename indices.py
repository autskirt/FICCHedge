# -*- coding: utf-8 -*-
"""指数库，由于期货存在生命周期，所以需要用对应的指数来计算波动率等变量"""

from WindPy import w
import pandas as pd
import sys

class Indices:
    #TODO  
    #是实例化一个、用一个列表还是一个一个实例化?
    def __init__(self, codes):
        self.data = None
        self.lastDay = None
        self.codes = codes

    def read_from_wind(self, start_time):
        #w.start()
        if len(w.tdays(start_time, "", "").Data[0])>1:
            data = w.wsd(self.codes, 'close', start_time, '')
            close = pd.DataFrame(data=data.Data, index=data.Codes, columns=data.Times).T
        else:
            data = w.wsq(self.codes, 'rt_last')
            close = pd.DataFrame(data=data.Data[0], index=data.Codes, columns=data.Times).T
        #close = pd.DataFrame(index=data.Times, columns=data.Codes)
        #for i  in range(len(close.columns)):
        #    close.iloc[:,i] = data.Data[i]
        close.index = pd.to_datetime(close.index)
        
        data_last = w.wsq(self.codes, 'rt_last')
        #close_last = pd.DataFrame(data=data_last.Data, index=data_last.Codes, columns=data_last.Times).T
        
        close_last = pd.DataFrame(data=data_last.Data[0], index=data_last.Codes, columns=data_last.Times).T
        close_last.index = pd.to_datetime(close_last.index)
        
        #close = (close.iloc[:-1,:]).append(close_last)
        close = pd.concat([close.iloc[:-1,:],close_last])
        
        #w.close
        return close

    def read_data(self, start_time):
        data = self.read_from_wind(start_time)
        #data = data.iloc[:-1,:] 2023.4
        self.lastDay = data.index[-1]
        #print(data)
        return data

