# -*- coding: utf-8 -*-


import pandas as pd
import numpy as np
import sys
import re
from WindPy import w
from datetime import datetime
from openpyxl import load_workbook
import os
from time import time

from indices import Indices
from futures import Futures
from asset import Asset


class OtcOption:
    def __init__(self, excel_name, sheet_name):
        self.excel_name = excel_name
        self.sheet_name = sheet_name
        self.index_codes = []
        self.future_codes = []
        self.start_time = None
        self.type = None
        self.info = None
        self.asset_num = 0
        self.abs_asset_list = []
        self.Is_issue = False
        self.Is_T = False
        self.Is_snowball = False
        self.Is_put = False
        self.observe_dates = []
        
        self.params = pd.Series()
        self.price = None
        self.times = None
        self.value = None
        self.delta = None
        self.dailyinfo = None
        self.futures_data = None

    def read_excel(self):
        info = pd.read_excel(self.excel_name, sheet_name=self.sheet_name, index_col=0)
        self.info = info['内容']
        print(self.sheet_name)
        for i in self.info.index:
            if re.match('资产', i):
                self.index_codes.append(self.info[i])
            elif re.match('挂钩资产', i):
                self.future_codes.append(self.info[i])
            elif re.match('模拟标志', i):
                self.Is_T = True
            elif re.match('敲入价', i):
                self.Is_snowball = True
        #print('Is_snowball:'+str(self.Is_snowball))
        if self.Is_T:
            print('A'*20)
            self.index_codes.pop()
        #print('index codes')
        #print(self.index_codes)
        self.asset_num = len(self.future_codes)
        self.start_time = self.info['起始日期'].strftime('%Y-%m-%d')
        # 判断该产品是否已经发行，是否需要进行存量管理
        cur = datetime.now().strftime('%Y-%m-%d')
        if cur >= self.start_time:
            self.Is_issue = True


    def read_from_wind_index(self, stocks,StrBegDay):
        w.start()
        data = w.wsd(stocks, 'close', StrBegDay, '')
        close = pd.DataFrame(index = data.Times, columns = data.Codes)
        for i in range(len(close.columns)):
            close.iloc[:,i] = data.Data[i]
        close.index = pd.to_datetime(close.index)
    
        data = w.wsd(stocks, 'oi', StrBegDay, '')
        oi = pd.DataFrame(index = data.Times, columns = data.Codes)
        for i in range(len(close.columns)):
            oi.iloc[:,i] = data.Data[i]
        oi.index = pd.to_datetime(close.index)
        Index = (close*oi).T.sum()/oi.T.sum()
        w.close
        return Index

    def set_option_params(self, tday):
        #凡是手动输入的都是全局变量
        #凡是从要素表里读取的是每只产品独有的
        # 2021.02.19
        #tday = self.dailyinfo.index[-1]
        indices = Indices(self.index_codes)
        print(self.index_codes)
        if self.index_codes:
            indices_data = indices.read_data('2024-06-01')
        else:
            indices_data = pd.DataFrame()
        if self.Is_T:
            stocks2 = ['T00.CFE', 'T01.CFE', 'T02.CFE',]
            indices_data['TFI.WI'] = self.read_from_wind_index(stocks2,'2024-06-01')
        #当日得到收盘价前进行维护，所以不包含当日数据（当日数据在收盘价更新前其数值和前日相同）
        self.indices_data = indices_data
        indices_data = self.indices_data.iloc[-252:,:]
        #print(indices_data)
        vol = np.log(indices_data).diff().std()*np.sqrt(252)#*1.2
        rho = np.log(indices_data).diff().corr()
        
        self.params['vol'] = vol.values
        #print(self.params['vol'])
        #print(type(self.params['vol']))
        self.params['rho'] = rho.values
        self.params['expRet'] = []
        self.params['observe_dates'] = []
        self.params['Is_put'] = False
        self.params['Is_in'] = False
        for i in self.info.index:
            if re.match('期望收益', i):
                self.params['expRet'].append(self.info[i])
            elif re.match('观察日', i):
                #print(self.info[i])
                #print(self.info['起始日期'])
                self.params['observe_dates'].append(w.tdayscount(self.info['起始日期'],self.info[i],"").Data[0][0])
            elif re.match('是否看跌',i):
                self.params['Is_put'] = True
            elif re.match('是否敲入', i):
                self.params['Is_in'] = True
        if self.Is_snowball:
            print('Is_put:'+str(self.params['Is_put']))
            print('Is_in:'+str(self.params['Is_in']))
        '''
        print('vol:'+str(self.params['vol']))
        print('rho:'+str(self.params['rho']))
        print('expRet:'+str(self.params['expRet']))
        '''
        self.params['B'] = self.info['敲出价']
        if self.Is_snowball:
            self.params['K'] = self.info['敲入价']
            self.params['coupon'] = 0.2
        else:
            self.params['K'] = self.info['执行价']
        self.params['H'] = self.params['B']-self.params['K']
        self.params['r'] = 0.025  # 无风险收益率   
        self.params['dt'] = 1/252
        self.params['T'] = w.tdayscount(tday,self.info['期末观察日'],"").Data[0][0]/252
        self.params['duration'] = w.tdayscount(self.info['起始日期'],self.info['结束日期'],"").Data[0][0]/252
        #self.params['T'] = (self.info['结束日期']-tday).days/365
        self.params['Type'] = self.info['期权种类']
        print(self.params['Type'])
        self.params['Ratio'] = []
        for i in range(self.asset_num):
            self.params['Ratio'].append(self.info['比例'+str(i+1)])
        #print('Ratio:'+str(self.params['Ratio']))
        self.params['Asset'] = indices_data.columns.tolist()

    def set_dailyinfo(self):
        futures = Futures(self.future_codes)
        # 在class Index中已经将返回值不包含当日数据
        self.futures_data = futures.read_data(self.info['起始日期'].strftime('%Y-%m-%d'))
        self.dailyinfo = self.futures_data.copy()
        
        #print(self.dailyinfo)
        for i in range(self.asset_num):
            self.dailyinfo.iloc[:,i] = self.dailyinfo.iloc[:,i]/self.dailyinfo.iloc[0,i]
            self.abs_asset_list.append(self.dailyinfo.iloc[-1,i])
            self.dailyinfo['Delta'+str(i+1)] = np.nan
            self.dailyinfo['Amount'+str(i+1)] = np.nan
            #self.dailyinfo['KnonckIn'+str(i+1)] = np.nan
            self.dailyinfo['IsKnock'+str(i+1)] = np.nan
        self.dailyinfo['Value(BP)'] = np.nan
        self.dailyinfo['Value(产品)'] = np.nan
        #print('abs_asset_list')
        #print(self.abs_asset_list)
        #print(self.dailyinfo)

    def monte_carlo(self, s):
        dt = self.params['dt']
        T = self.params['T']
        nTimes = int(T/dt)
        nPaths = 120000
        vol = self.params['vol']
        rho = self.params['rho']
        expRet = self.params['expRet']
        price_list_df = []
        #print(vol)
        #print(type(vol))
        if len(vol) == 1:
            #print("vol1")
            rnd = np.random.randn(nTimes,nPaths)
            simuRet = expRet[0]*dt + rnd*vol*np.sqrt(dt)
            simuRet = np.insert(simuRet, 0, values=np.zeros(nPaths), axis=0)
            price = pd.DataFrame(index=np.arange(nTimes+1),data=simuRet)
            s = np.ones((nTimes+1, nPaths))*s
            #s = pd.Series(index=np.arange(nTimes+1),data=term)
            price = s*np.exp(price.cumsum())
            #times = np.arange(0,nTimes+1)*dt
            price_list_df.append(price.T)
            #print(price.T)
        else:
            cov = np.multiply(np.matrix(vol).T*np.matrix(vol),np.matrix(rho))
            rnd = np.random.multivariate_normal(np.zeros(len(vol)), cov,(nTimes,nPaths))
            for i in range(self.asset_num):
                simu_price = rnd[:,:,i]
                simu_price1 = expRet[i]*dt+simu_price*np.sqrt(dt)
                simu_price1 = np.insert(simu_price1, 0, values=np.zeros(nPaths), axis=0)
                price1 = pd.DataFrame(index=np.arange(nTimes+1),data=simu_price1)
                price1 = s[i]*np.exp(price1.cumsum()*self.params['Ratio'][i])
                price1 = price1.T   # (nTimes,nPaths)->(nPaths,nTimes)
                #times = np.arange(0,nTimes+1)*dt
                price_list_df.append(price1)
            #return price1, times
        return price_list_df
  

    # 核心模块
    def option_pricing(self, pricing_type, s=None, real_data=None):
        payoff_list = []
        extime_list = []
        extime_index = pd.DataFrame().index
        extime_index2 = pd.DataFrame().index
        # TODO
        # 把这些属性放在全局属性里，这样估值（读更多复杂字段）和定价（读另外一些不重合字段的），就可以统一
        H = self.params['H']
        B = self.params['B']
        K = self.params['K']
        r = self.params['r']
        dt = self.params['dt']
        T = self.params['T']
        nTimes = int(T/dt)
        times = nTimes * dt
        #TODO 
        #   How price_list_df gooten
        #   1.simulation     1.1 from init Day(s=1)     1.2 from current Day
        #   2.real_data
        if pricing_type == 'pricing':
            price_list_df = self.monte_carlo(np.ones(self.asset_num))
        elif pricing_type == 'history_test':
            price_list_df = real_data
        elif pricing_type == 'estimation':
            price_list_df = self.monte_carlo(s)
        #if self.asset_num == 1:
            #TODO
        #elif:
        for i in range(self.asset_num):
            #   定价.py         s[i]=1, simu_price(100000, 3months)
            #   HisTest.py      simu_price(500days, 3months)
            #   估值.py         s[i]=current_price/init_price, simu_price(100000, 3months-T_past)
            #   s[i], simu_price (nPaths,nTimes)
            #   price_list_df[i]  (nPaths,nTimes)
            #   expected goal:
            #   asset = Asset(price, self.params)
            
            asset = Asset(i, price_list_df[i], self.params)
            
            #asset = Asset(s[i], simu_price[:,:,i], option_type, self.params, i)
            payoff, extime = asset.compute_payoff()
            #print('时间lll：',t21-t11)
            payoff_list.append(payoff)
            extime_list.append(extime)
            #extime_index = extime_index | extime[extime==1].index
            #extime_index2 = extime_index2 & extime[extime==0].index
            extime_index = extime_index.union(extime[extime==1].index)
            extime_index2 = extime_index2.intersection(extime[extime==0].index)
        #print('时间loop：',t2-t1)
        # Aggregation
        payoff_all = pd.concat(payoff_list, axis=1)
        extime_all = pd.concat(extime_list, axis=1)
        #value = pd.Series(index=extime_all.index, data=0.0)
        #Isknock_index = extime_all.apply(lambda x: x.sum()>0, axis=1)
        #value[np.bitwise_not(Isknock_index)] = payoff_all.apply(lambda x: max(x), axis=1)
        value = payoff_all.apply(lambda x: max(x), axis=1)
        # 每条路径有至少一个资产敲出
        if self.params['Type'] in ['鲨鱼鳍','双向鲨鱼鳍','单向鲨鱼鳍']:
            value[extime_index] = H/2
        else:
            value[extime_index] = B-K
        """
        #value[np.bitwise_not(Isknock_index)] = payoff_all.apply(lambda x: max(x), axis=1)
        value[np.bitwise_not(Isknock_index)] = payoff_all.apply(lambda x: max(x), axis=1)
        """
        value = np.exp(-r*times)*np.mean(value)
        if self.params['Type'] =='小雪球':
            value = np.mean(payoff)
        
        #print('循环时间_MonteCarlo：', run_time1, run_time2, run_time4, run_time3, run_time5)

        return value

        
    def option_delta(self, t, tday, value, ratio, s):
        # 2021.02.19
        #tday = self.dailyinfo.index[-1]
        #value = self.option_pricing(self.abs_asset_list)
        money = self.info['发行规模']*1.0e4
        self.delta = pd.Series(index=self.params['Asset'], data=0.0)

        for i in range(0, self.asset_num):
            # 2021.02.19
            #temp_abs = self.abs_asset_list[:]
            #print('-'*20)
            #print(s)
            '''
            temp_abs = list(s)
            temp_abs[i] = temp_abs[i]*(1+ratio/self.params['Ratio'][i])
            value_delta = self.option_pricing('estimation', s=temp_abs)
            self.delta[i] = (value_delta-value)/(s[i]*ratio)
            '''
            temp_abs_up = list(s)
            temp_abs_down = list(s)
            temp_abs_up[i] = temp_abs_up[i]*(1+ratio/self.params['Ratio'][i])
            temp_abs_down[i] = temp_abs_down[i]*(1-ratio/self.params['Ratio'][i])
            value_up = self.option_pricing('estimation', s=temp_abs_up)
            value_down = self.option_pricing('estimation', s=temp_abs_down)
            self.delta[i] = (value_up-value_down)/(s[i]*ratio)/2
            
            #print("q"*20)
            #print(temp_abs)
            #print(value)
            #print(value_delta)
            #self.delta[i] = (value_delta-value)/(self.abs_asset_list[i]*ratio)
            # 小雪球最低delta为0.2，直到涨幅达到1.01
            if (self.params['Type']=='小雪球') and (self.params['Is_put']==False):
                print("initial delta: " +str(self.delta[i]))
                min_delta = 0.1*(s[i]<1.05)
                self.delta[i] = max(self.delta[i],min_delta)
            '''
            #print(self.params)
            print("%"*20)
            print("value: "+ str(value))
            print("value_delta: "+str(value_delta))
            print("ratio: "+ str(ratio))
            print("delta: " +str(self.delta[i]))
            '''
            print("current asset price: " +str(s[i]))
            self.dailyinfo.loc[tday, 'Delta'+str(i+1)] = self.delta[i]
            #self.dailyinfo.loc[tday, 'Amount'+str(i+1)] = money*self.delta[i]*self.info['参与率(年化)']\
            #    /self.futures_data.iloc[-1,i]/self.info['合约乘数'+str(i+1)]*self.params['Ratio'][i]
            
            if (self.delta[i] < 0) and ((self.params['Type']=='鲨鱼鳍') or (self.params['Type']=='小雪球' and self.params['Is_put']==False)):
                self.dailyinfo.loc[tday, 'Amount'+str(i+1)] = 0
            #elif self.params['Type']=='小雪球':
            else:
                self.dailyinfo.loc[tday, 'Amount'+str(i+1)] = money*self.delta[i]*self.info['参与率(年化)']*self.params['duration']\
                    /self.futures_data.iloc[t,i]/self.info['合约乘数'+str(i+1)]*self.params['Ratio'][i]
            #else:
            #    self.dailyinfo.loc[tday, 'Amount'+str(i+1)] = money*self.delta[i]*self.info['参与率(年化)']*self.params['duration']\
            #        /self.futures_data.iloc[t,i]/self.info['合约乘数'+str(i+1)]*self.params['Ratio'][i]
            print("Amount: " +str(self.dailyinfo.loc[tday, 'Amount'+str(i+1)]))
            #print(s)
            #print(self.futures_data.iloc[0,i])
        #print('***********************************')
        print(self.delta)
        #print(self.dailyinfo.loc[tday,:])
        return self.delta

    def add_daywise_value(self, tday, value, s):
        # 这个放return value前
        # 2021.02.19
        #tday = self.dailyinfo.index[-1]
        T = self.params['T']
        X = self.info['参与率(年化)']
        self.dailyinfo.loc[tday,'Value(BP)'] = value*1.0e4
        self.dailyinfo.loc[tday,'Value(产品)'] = value*1.0e4/self.params['duration']*X
        for i in range(self.asset_num):
            """
            if self.abs_asset_list[i] > self.params['B']:
                self.dailyinfo.loc[tday, 'IsKnock'+str(i+1)] = 'y'
            else:
                self.dailyinfo.loc[tday, 'IsKnock'+str(i+1)] = 'n'
            """
            
            #if s[i] < self.params['D']:
            #    self.dailyinfo.loc[tday, 'KnonckIn'+str(i+1)] = 'y'
            #else:
            #    self.dailyinfo.loc[tday, 'KnonckIn'+str(i+1)] = 'n'
            if (self.params['Is_put'] and s[i] < self.params['B']) or\
                (not self.params['Is_put'] and s[i] > self.params['B']):
                self.dailyinfo.loc[tday, 'IsKnock'+str(i+1)] = 'y'
            else:
                self.dailyinfo.loc[tday, 'IsKnock'+str(i+1)] = 'n'
