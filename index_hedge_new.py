# -*- coding: utf-8 -*-
"""
合并的指数规模计算和期货仓位计算程序
严格按照原始逻辑，只是消除中间文件依赖
"""

import re
import pandas as pd
import numpy as np
from datetime import date
from WindPy import w
import warnings

warnings.filterwarnings("ignore")

def calculate_index_amounts():
    """计算指数规模 - 完全复制index_amt.py的逻辑"""
    # 台账读数
    filepath = "浮动收益凭证流水.xlsx"
    tp = pd.read_excel(filepath,index_col=0)

    today = pd.to_datetime(date.today())
    t = today.strftime("%Y%m%d")

    asset_path = "asset_list.xlsx"
    asset_list = pd.read_excel(asset_path,index_col=0,dtype={"类型":"str"})

    # 提取序号非空且未到期的产品
    products = tp[(tp["起息日"]<today) & (tp["到期日"]>today)]

    #%% 计算未到期产品规模
    w.start()
    amt = pd.DataFrame(columns = ["THETA.WI",'SIGMA.WI','SIGMA2.WI','FACTOR2.WI'])#,index=["amt"])
    for idx in amt.columns:
        df = products[products["挂钩标的"] == idx]
        idx_amt =0.0
        for i in df.index:
            idx_amt +=df.loc[i,'规模']*df.loc[i,'斜率']
            temp = w.wsd(idx, 'close', df.loc[i,'起息日'], '').Data[0]
            if (np.max(temp)/temp[0]-1)>=df.loc[i,'敲出水平']:
                print(df.loc[i,'产品简称']+"已敲出")
        amt[idx] = [idx_amt]
    w.close()
    amt.to_excel("指数规模.xlsx")
    print(amt)
    return amt


def calculate_positions(amt):
    """计算仓位 - 完全复制index_hedge.py的逻辑，使用全局变量"""
    w.start()

    start_date = '2025-3-15'
    #end_date = '2025-1-3'
    end_date = date.today().strftime('%Y-%m-%d')

    #%%
    def compute_feasible_contract(asset, code, flag):
        #start_date = str(w.tdays().Times[0]-timedelta(2))
        #end_date = str(w.tdays().Times[0]-timedelta(1))
        start_date = str(asset.index[-2])
        end_date = str(asset.index[-1])
        temp = w.wset("futurecc","startdate="+start_date+";enddate="+end_date+";wind_code="+code)
        panel_t = pd.DataFrame(index=temp.Fields, data=temp.Data, columns=temp.Codes).T

        # volume 成交量    oi 持仓量
        temp = w.wsd(list(panel_t['wind_code'].values), flag, start_date, end_date)
        vol = pd.DataFrame(data=temp.Data, index=temp.Codes, columns=temp.Times).T
        vol.index = pd.to_datetime(vol.index)

        temp = w.wsd(list(panel_t['wind_code'].values), 'close', start_date, end_date)
        close = pd.DataFrame(data=temp.Data, index=temp.Codes, columns=temp.Times).T
        close.index = pd.to_datetime(close.index)
        
        tt = pd.Series()
        ret_t = pd.Series()
        # 当月的不做，次月的不做，在剩下的合约里面选持仓量最大的，国债期货除外
        if code[0] == 'T':
            maincontract = vol[-1:].iloc[:,1:] 
            maincontract = maincontract.idxmax(axis=1).item()
        else:
            maincontract = vol[-1:].iloc[:,2:] 
            maincontract = maincontract.idxmax(axis=1).item()
        #tt = tt.append(pd.Series(index=[vol.index[-1]], data=maincontract))
        tt = pd.concat([tt,pd.Series(index=[vol.index[-1]], data=maincontract)])
        temp = close.loc[vol.index[-1], maincontract]
        #ret_t = ret_t.append(pd.Series(index=[vol.index[-1]], data=temp))
        ret_t = pd.concat([ret_t,pd.Series(index=[vol.index[-1]], data=temp)])
        return ret_t, tt

    #
    def compute_position(total_money, df_weight):
        asset_list = df_weight.columns
        multiplier = panel.loc[asset_list.to_list(), '合约乘数']
        position = pd.DataFrame(index=[df_weight.index[-1]], columns=asset_list, data=0)
        contract_list = []
        for item in asset_list:
            temp, contract = compute_feasible_contract(asset, panel.loc[item, 'code'], 'oi')
            contract_list.append(contract[0])
            #print(contract)
            weight = df_weight.loc[df_weight.index[-1], item]
            position.loc[:,item] = total_money * weight /(temp.item() * multiplier[item])
            position.loc[:,item] = position.loc[:,item] * 10000
        position.columns = contract_list
        print(position.T)  
        return position

    #%% Backbone of real trade date for contract computing
    temp = w.wsd(['CGBFRI10.CCI', '000300.SH'], 'close', start_date, end_date)
    asset = pd.DataFrame(data=temp.Data, index=temp.Codes, columns=temp.Times).T
    asset.index = pd.to_datetime(asset.index)
    asset = asset.dropna()
    panel = pd.read_excel('品种映射表.xlsx', index_col=0)

    #%% 
    # amt = pd.read_excel("指数规模.xlsx",index_col=0)  # 这行被内存传递替代
    print(amt)
    weight_path = '指数对冲权重.xlsx'
    df_weight1 = pd.read_excel(weight_path, index_col=0, sheet_name='SIGMA指数')
    money1 = amt["SIGMA.WI"][0]
    position1 = compute_position(money1, df_weight1)
    #print(position1.T)
    df_weight2 = pd.read_excel(weight_path, index_col=0, sheet_name='SIGMA2指数')
    money2 = amt["SIGMA2.WI"][0]
    position2 = compute_position(money2, df_weight2)
    #print(position2.T)
    df_weight3 = pd.read_excel(weight_path, index_col=0, sheet_name='THETA指数')
    money3 = amt["THETA.WI"][0]
    position3 = compute_position(money3, df_weight3)
    #print(position3.T)
    df_weight4 = pd.read_excel(weight_path, index_col=0, sheet_name='FACTOR2指数')
    money4 = amt["FACTOR2.WI"][0]
    position4 = compute_position(money3, df_weight3)  # 保持原代码的bug

    temp = pd.concat([position1, position2, position3, position4],ignore_index=True)
    #temp = pd.concat([temp, position3],ignore_index=True)
    temp = temp.fillna(0)
    temp_ = temp.cumsum()
    total_position = temp_[-1:]
    total_position.to_excel("total_position.xlsx")
    print(total_position.T)
    
    w.close()
    return total_position


def main():
    """主函数 - 合并两个程序但保持原逻辑"""
    print("开始计算指数规模...")
    # 1. 计算指数规模（index_amt.py的逻辑）
    amt = calculate_index_amounts()
    
    print("开始计算期货仓位...")
    # 2. 计算期货仓位（index_hedge.py的逻辑）- 直接传入amt，不读取excel
    total_position = calculate_positions(amt)
    
    return total_position


if __name__ == '__main__':
    result = main()