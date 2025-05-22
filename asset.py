# -*- coding: utf-8 -*-
"""挂钩资产"""

from WindPy import w
import pandas as pd
import numpy as np
import sys
from time import time

class Asset:
    def __init__(self, num, price_df, params):
        self.num = num
        self.knock_in = None
        self.knock_out = None
        self.payoff = None
        self.price_df = price_df
        #self.simu_price = simu_price    #(nTimes,nPaths)
        self.params = params
        self.option_type = params['Type']

    """
    # simu_price: (nTimes,nPaths)
    def compute_price(self):
        dt = self.params['dt']
        T = self.params['T']
        nTimes = int(T/dt)
        nPaths = 100000
        simu_price1 = self.simu_price*np.sqrt(dt)
        #print('simu_price1')
        #print(simu_price1)
        simu_price1 = np.insert(simu_price1, 0, values=np.zeros(nPaths), axis=0)
        #print('simu_price1')
        #print(simu_price1)
        price1 = pd.DataFrame(index=np.arange(nTimes+1),data=simu_price1)
        #print('price1')
        #print(price1)
        #print('ratio')
        #print(self.params['Ratio'])
        price1 = self.s*np.exp(price1.cumsum()*self.params['Ratio'][self.order])
        price1 = price1.T   # (nTimes,nPaths)->(nPaths,nTimes)
        times = np.arange(0,nTimes+1)*dt
        
        return price1, times
    """

    """
    def option_pricing(self, s, simu_price, params):
        #r = params['r']
        option_type = params['Type']
        if option_type == "鲨鱼鳍":
            payoff = self.payoff_sharkfin(s, simu_price, params)
        
        #value = np.mean(np.exp(-r*times[-1])*payoff)
        #value = np.exp(-r*times[-1])*payoff

        return payoff
    """

    def compute_payoff(self):
        if self.option_type ==  "价差":
            return self.payoff_spread()
        elif self.option_type ==  "鲨鱼鳍":
            return self.payoff_sharkfin()
        elif self.option_type == "双向鲨鱼鳍":
            return self.payoff_bisharkfin()  
        elif self.option_type == "敲入价差":
            return self.payoff_snowball()
        elif self.option_type == "小雪球":
            return self.payoff_little_snowball()
        
    # 计算回报函数：价差
    
    def payoff_spread(self):
        K = self.params['K']
        B = (self.params['B']-1)/self.params['Ratio'][self.num]+1
        #B = self.params['B']
        dt = self.params['dt']
        T = self.params['T']
        nTimes = int(T/dt)

        payoff = pd.Series(index=self.price_df.index,data=0.0)
        exTime = pd.Series(index=self.price_df.index,data=0.0)
        for i in range(1, nTimes):
            # 是否敲出
            tRet = self.price_df.loc[exTime[exTime==0].index, self.price_df.columns[i]]
            IsExc = tRet.loc[tRet.T>=B]
            exTime[IsExc.index] = 1 #这个才是重点，用于上层汇总判断用
            payoff[IsExc.index] = B-K
        IsExc2 = tRet.loc[(tRet.T>=B)==0]
        lastPayoff = list(map(lambda x:max(self.params['Ratio'][self.num]*(x-K),0),(tRet.loc[IsExc2.index].T)))    
        payoff[IsExc2.index] = lastPayoff
        exTime[IsExc2.index] = 0
        
        return payoff, exTime

    # 计算回报函数（鲨鱼鳍）
    def payoff_sharkfin(self):
        
        B = (self.params['B']-1)/self.params['Ratio'][self.num]+1
        #B = self.params['B']
        K = self.params['K']
        H = self.params['H']/2
        dt = self.params['dt']
        T = self.params['T']
        nTimes = int(T/dt)

        payoff = pd.Series(index=self.price_df.index,data=0.0)
        exTime = pd.Series(index=self.price_df.index,data=0.0)
        #for i in range(1,len(times)-1):
        for i in range(1, nTimes):
            # 是否敲出
            tRet = self.price_df.loc[exTime[exTime==0].index, self.price_df.columns[i]]
            IsExc = tRet.loc[tRet.T>=B]
            exTime[IsExc.index] = 1 #这个才是重点，用于上层汇总判断用
            payoff[IsExc.index] = H 
        # t=T 时刻    
        #t = len(times)-1
        #tRet = price.loc[exTime[exTime==0].index,price.columns[t]]
        #IsExc1 = tRet.loc[(tRet.T>=B)>0,:]
        #payoff[IsExc1.index] = H
        #exTime[IsExc1.index] = 1

        IsExc2 = tRet.loc[(tRet.T>=B)==0]
        
        lastPayoff = list(map(lambda x:max(self.params['Ratio'][self.num]*(x-K),0),(tRet.loc[IsExc2.index].T)))    
        payoff[IsExc2.index] = lastPayoff
        exTime[IsExc2.index] = 0
        
        return payoff, exTime
    
    # 计算回报函数：双边鲨鱼鳍
    def payoff_bisharkfin(self):
        K = self.params['K']
        #B = self.params['B']
        B = (self.params['B']-1)/self.params['Ratio'][self.num]+1
        H = self.params['H']/2
        dt = self.params['dt']
        T = self.params['T']
        nTimes = int(T/dt)

        payoff = pd.Series(index=self.price_df.index,data=0.0)
        exTime = pd.Series(index=self.price_df.index,data=0.0)
        #for i in range(1,len(times)-1):
        for i in range(1, nTimes):
            # 是否敲出
            tRet = self.price_df.loc[exTime[exTime==0].index, self.price_df.columns[i]]
            IsExc = tRet.loc[abs(tRet.T-1)>=B-1]
            exTime[IsExc.index] = 1 #这个才是重点，用于上层汇总判断用
            payoff[IsExc.index] = H
        # t=T 时刻    
        #t = len(times)-1
        #tRet = price.loc[exTime[exTime==0].index,price.columns[t]]
        #IsExc1 = tRet.loc[(tRet.T>=B)>0,:]
        #payoff[IsExc1.index] = H
        #exTime[IsExc1.index] = 1

        # 最后一天可能没有落在观察点上，所以要单独拎出来
        tRet = self.price_df.loc[exTime[exTime==0].index, self.price_df.columns[nTimes]]
        
        IsExc2 = tRet.loc[(abs(tRet.T-1)>=B-1)==0]
        lastPayoff = list(map(lambda x:max(self.params['Ratio'][self.num]*(abs(x-1)-(K-1)),0),(tRet.loc[IsExc2.index].T)))    
        payoff[IsExc2.index] = lastPayoff
        exTime[IsExc2.index] = 0
        
        return payoff, exTime

    # 计算回报函数（类雪球）
    def payoff_snowball(self):
        K = self.params['K']
        B = (self.params['B']-1)/self.params['Ratio'][self.num]+1
        #B = self.params['B']
        D = self.params['D']
        dt = self.params['dt']
        T = self.params['T']
        nTimes = int(T/dt)
        payoff = pd.Series(index=self.price_df.index,data=0.0)
        knockIn = pd.Series(index=self.price_df.index, data=False)
        exTime = pd.Series(index=self.price_df.index,data=0.0)
        for i in range(1, nTimes):
            # 是否敲入
            # 是否敲出
            tRet = self.price_df.loc[exTime[exTime==0].index, self.price_df.columns[i]]
            knockIn[tRet[tRet<=D].index] = True
            #加入未敲入的判断
            IsIn = knockIn[knockIn]
            IsExc = tRet[tRet>=B]
            exTime[(IsExc.index)&(IsIn.index)] = 1 #这个才是重点，用于上层汇总判断用
            payoff[(IsExc.index)&(IsIn.index)] = B-K
        IsExc2 = tRet.loc[(tRet.T>=B)==0]
        lastPayoff = list(map(lambda x:max(self.params['Ratio'][self.num]*(x-K),0),(tRet.loc[(IsExc2.index)&(IsIn.index)].T)))    # key point
        payoff[(IsExc2.index)&(IsIn.index)] = lastPayoff
        exTime[(IsExc2.index)&(IsIn.index)] = 0
        #未敲入，可以不加
        #payoff[knockIn[np.bitwise_not(knockIn)]] = 0.0
        #exTime[knockIn[np.bitwise_not(knockIn)]] = 0
        print('333'*120)
        print(exTime)
        return payoff, exTime

    # 计算回报函数（小雪球）
    def payoff_little_snowball(self):
        K = self.params['K']
        B = self.params['B']
        dt = self.params['dt']
        T = self.params['T']
        duration = self.params['duration']
        nTimes = int(T/dt)
        totalTimes = int(duration/dt)
        
        #payoff = pd.Series(index=self.price_df.index,data=0.03*duration*np.exp(-self.params['r']*T))
        payoff = pd.Series(index=self.price_df.index,data=0.0)
        exTime = pd.Series(index=self.price_df.index,data=0.0)
        inTime = pd.Series(index=self.price_df.index,data=1.0*self.params['Is_in'])
        
        for i in range(1,nTimes):
            # 只观察未敲出路径
            tRet = self.price_df.loc[exTime[exTime==0].index, self.price_df.columns[i]]
            # 是否敲入
            if self.params['Is_put']:
                IsIn = tRet.loc[tRet>=K]
            else:
                IsIn = tRet.loc[tRet<=K]
            inTime[IsIn.index] = 1
            t = i+totalTimes-nTimes
            # 观察日和到期日观察是否敲出
            if (t in self.params['observe_dates']) or (i == nTimes-1):
                if self.params['Is_put']:
                    IsExc = tRet.loc[tRet.T<=B]
                else:
                    IsExc = tRet.loc[tRet.T>=B]
                exTime[IsExc.index] = 1
                payoff[IsExc.index] = self.params['coupon']*t*dt*np.exp(-self.params['r']*i*dt)
        #IsExc2 = tRet.loc[(tRet.T>=B)==0]
        payoff[(exTime==0)&(inTime==1)] = -np.abs(K-B)*np.exp(-self.params['r']*T)
        #payoff[(exTime==0)&(inTime==0)] = self.params['coupon']*duration*np.exp(-self.params['r']*T)
        return payoff, exTime

    # compute knock_out rate(spread)
    
    
    # compute knock_out rate(sharkfin)


    # compute knock_out rate(snowball)