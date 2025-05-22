# -*- coding: utf-8 -*-
"""
删除delta_zbx依赖的版本 - 只保留核心计算逻辑
"""

import re
import pandas as pd
import numpy as np
from datetime import date
from WindPy import w
import warnings
from time import time
from otcoption import OtcOption

w.start()
warnings.filterwarnings("ignore")

def create_element_summary_data():
    """生成要素表数据，返回内存中的数据而不是写Excel"""
    
    filepath = "浮动收益凭证流水.xlsx"
    total_products = pd.read_excel(filepath, index_col=0)
    today = pd.to_datetime(date.today())
    
    asset_path = "asset_list.xlsx"
    asset_list = pd.read_excel(asset_path, index_col=0, dtype={"类型": "str"})
    
    # 提取序号非空且未到期的产品
    products = total_products.loc[total_products.index[~pd.isna(total_products['挂钩标的']) &
                                                       ~pd.isna(total_products['到期日']) &
                                                       pd.isna(total_products['收益情况'])], ]
    
    snowball_data = {}  # 小雪球数据
    other_data = {}     # 其他产品数据
    
    for i in products.index:
        if today < products['起息日'][i]:
            continue
            
        df = pd.DataFrame(index=['内容'])
        df['起始日期'] = products['起息日'][i]
        df['结束日期'] = products['到期日'][i]
        df['期末观察日'] = w.tdaysoffset(-1, products['到期日'][i], "").Data[0][0]
        
        if df['期末观察日']['内容'] <= today:
            continue
            
        df['发行规模'] = products['规模'][i]
        
        # 通过产品名称和收益结构判断期权种类
        rate = re.findall(r"\d+\.\d*", products['收益区间'][i])
        if '小雪球' in products['产品简称'][i]:
            df['期权种类'] = '小雪球'
        elif '双盈' in products['产品简称'][i]:
            df['期权种类'] = '双向鲨鱼鳍'
        elif len(rate) == 2:
            df['期权种类'] = '价差'
        else:
            df['期权种类'] = '鲨鱼鳍'
        
        # 提取标的资产，跳过指数类
        asset = re.split(r'[;；，,]', products['挂钩标的'][i])
        if set(asset) & set(['SIGMA.WI', 'SIGMA2.WI', 'THETA.WI', 'FACTOR.WI', 'FACTOR2.WI']):
            continue
            
        # 提取每个资产的要素
        for j in range(len(asset)):
            df['资产' + str(j + 1)] = asset[j]
            df['挂钩资产' + str(j + 1)] = asset[j]
            df['比例' + str(j + 1)] = 1
            df['合约乘数' + str(j + 1)] = asset_list.loc[asset[j], '合约乘数']
            df['期望收益' + str(j + 1)] = asset_list.loc[asset[j], '期望收益']
            if len(asset) > 1:
                df['比例' + str(j + 1)] = asset_list.loc[asset[j], '比例']
        
        product_name = re.split(r'[\(（]', products['产品简称'][i].replace('\n', ''))[0]
        
        # 小雪球是否敲入&其他产品前一天收盘价是否敲出
        if df.loc['内容', '期权种类'] == '小雪球':
            temp = w.wsd(asset, 'close', df.loc['内容', '起始日期'], '').Data
            df['敲出收益'] = float(rate[-1]) / 100
            df['固定收益'] = float(rate[0]) / 100
            temp = temp[0]
            df['未敲出收益'] = float(rate[1]) / 100
            df['敲出价'] = products['敲出水平'][i]
            df['敲入价'] = products['斜率'][i]
            df['参与率(年化)'] = (df['敲出收益'] - df['未敲出收益']) / abs(df['敲出价'] - df['敲入价'])
            
            if df.loc['内容', '敲入价'] > df.loc['内容', '敲出价']:
                df['是否看跌'] = '是'
                if max(temp) > temp[0] * products['斜率'][i]:
                    df['是否敲入'] = '是'
                    print(re.split(r'[\(（]', products['产品简称'][i].replace('\n', ''))[0] + '已敲入')
            elif min(temp) < temp[0] * products['斜率'][i]:
                df['是否敲入'] = '是'
                print(re.split(r'[\(（]', products['产品简称'][i])[0] + '已敲入')
                
            observe_days = re.findall(r"\d+\.\d*", products['观察日'][i])
            for t in range(len(observe_days)):
                day = re.split(r"\.", observe_days[t])
                day = date(today.year, int(day[0]), int(day[1]))
                if day < df.loc['内容', '起始日期'].date():
                    day = date(today.year + 1, day.month, day.day)
                if day < today.date():
                    continue
                df['观察日' + str(t + 1)] = day
            
            snowball_data[product_name] = df
            
        else:
            temp = w.wsd(asset, 'close', df.loc['内容', '起始日期'], '').Data
            IsKnock = False
            df['敲出收益'] = float(rate[-1]) / 100
            df['固定收益'] = float(rate[0]) / 100
            df['最高收益'] = float(rate[1]) / 100
            df['参与率(年化)'] = products['斜率'][i]
            df['敲出价'] = products['敲出水平'][i] + 1
            df['执行价'] = round(df.loc['内容', '敲出价'] - (df.loc['内容', '最高收益'] - df.loc['内容', '固定收益']) / df.loc['内容', '参与率(年化)'], 2)
            
            if df.loc['内容', '起始日期'] < today:
                for n in range(len(asset)):
                    k = (np.array(temp[n]) / temp[n][0] - 1) * df.loc['内容', '比例' + str(n + 1)]
                    if df.loc['内容', '期权种类'] == "双向鲨鱼鳍":
                        k = abs(k)
                    if max(k) > products['敲出水平'][i]:
                        print(products['产品简称'][i] + '已敲出 ' + asset[n] + " 期初价:" + str(temp[n][0]) + " 最近收盘价:" + str(temp[n][-1]))
                        IsKnock = True
            
            # 如果已敲出，则无需对冲
            if not IsKnock:
                other_data[product_name] = df
    
    return snowball_data, other_data

def save_excel_files(snowball_data, other_data):
    """保存Excel文件 - 和原来一样的格式"""
    def save_to_excel(data, filename):
        if not data:
            return
        writer = pd.ExcelWriter(filename, engine='xlsxwriter', datetime_format='YYYY/MM/DD')
        cell_format = writer.book.add_format({'align': 'center'})
        
        for product_name, df in data.items():
            df.T.to_excel(writer, sheet_name=product_name)
            worksheet = writer.sheets[product_name]
            worksheet.set_column("A:B", 13, cell_format)
        
        writer.close()
    
    save_to_excel(snowball_data, "小雪球汇总要素表.xlsx")
    save_to_excel(other_data, "汇总要素表.xlsx")

class OptimizedOtcOption(OtcOption):
    """优化后的OtcOption类，去除delta_zbx依赖"""
    
    def __init__(self, product_name, data_df):
        # 初始化父类的所有属性
        super().__init__('', product_name)
        self.info = data_df.loc['内容'] if data_df is not None else None
        self.sheet_name = product_name
        
        # 解析资产代码
        if data_df is not None:
            self.index_codes = []
            self.future_codes = []
            for col in data_df.columns:
                if re.match(r'^资产\d+$', col):
                    self.index_codes.append(self.info[col])
                elif re.match(r'^挂钩资产\d+$', col):
                    self.future_codes.append(self.info[col])
            
            # 检查特殊标志
            for i in self.info.index:
                if re.match('敲入价', str(i)):
                    self.Is_snowball = True
                elif re.match('模拟标志', str(i)):
                    self.Is_T = True
            
            if self.Is_T and self.index_codes:
                self.index_codes.pop()
                
            self.asset_num = len(self.future_codes)
            self.start_time = self.info['起始日期'].strftime('%Y-%m-%d')
            
            # 判断是否已发行
            from datetime import datetime
            cur = datetime.now().strftime('%Y-%m-%d')
            if cur >= self.start_time:
                self.Is_issue = True
            else:
                self.Is_issue = False

    def monte_carlo(self, s):
        """优化的蒙特卡洛模拟 - 提升速度同时保证精度，保持DataFrame格式兼容性"""
        dt = self.params['dt']
        T = self.params['T']
        nTimes = int(T/dt)
        nPaths = 200000  # 保证精度的路径数
        vol = self.params['vol']
        rho = self.params['rho']
        expRet = self.params['expRet']
        price_list_df = []
        
        if len(vol) == 1:
            # 单资产优化 - 先用numpy计算，再转DataFrame
            rnd = np.random.standard_normal((nTimes, nPaths))
            simuRet = expRet[0] * dt + rnd * vol * np.sqrt(dt)
            simuRet = np.vstack([np.zeros(nPaths), simuRet])
            price_np = s * np.exp(np.cumsum(simuRet, axis=0))
            
            # 转换为DataFrame以保持兼容性
            price_df = pd.DataFrame(price_np.T, 
                                   index=range(nPaths), 
                                   columns=range(nTimes + 1))
            price_list_df.append(price_df)
        else:
            # 多资产优化
            cov = vol[:, np.newaxis] * vol[np.newaxis, :] * rho
            rnd = np.random.multivariate_normal(np.zeros(len(vol)), cov, (nTimes, nPaths))
            
            for i in range(self.asset_num):
                simu_price = rnd[:, :, i]
                simu_price1 = expRet[i] * dt + simu_price * np.sqrt(dt)
                simu_price1 = np.vstack([np.zeros(nPaths), simu_price1])
                price_np = s[i] * np.exp(np.cumsum(simu_price1 * self.params['Ratio'][i], axis=0))
                
                # 转换为DataFrame以保持兼容性
                price_df = pd.DataFrame(price_np.T, 
                                       index=range(nPaths), 
                                       columns=range(nTimes + 1))
                price_list_df.append(price_df)
                
        return price_list_df

def run_estimation_on_data(data_dict, data_type_name):
    """去除delta_zbx依赖的估值函数 - 只在内存中计算"""
    if data_type_name == "小雪球":
        # 小雪球返回每个产品的详细amount
        product_results = {}
    else:
        # 非小雪球汇总amount
        asset_list = dict()
    
    print(f"\n开始处理{data_type_name}产品，共{len(data_dict)}个...")
    
    for idx, (product_name, product_df) in enumerate(data_dict.items()):
        print(f'[{idx+1}/{len(data_dict)}] 处理产品: {product_name}', end=' ... ')
        start_time = time()
        
        try:
            # 使用优化的OtcOption
            option = OptimizedOtcOption(product_name, product_df)
            
            if option.Is_issue:
                # 设置日常信息
                option.set_dailyinfo()
                
                # 获取最后一个交易日
                tday = option.dailyinfo.index[-1]
                
                # 设置期权参数
                option.set_option_params(tday)
                
                # 计算估值
                value = option.option_pricing('estimation', s=option.abs_asset_list)
                
                # 计算delta
                option.option_delta(0, tday, value, 0.003, option.abs_asset_list)
                
                # 添加日常估值数据
                option.add_daywise_value(tday, value, option.abs_asset_list)

                if data_type_name == "小雪球":
                    # 小雪球：记录每个产品的详细信息
                    product_assets = {}
                    for i in range(0, option.asset_num):
                        asset_code = option.future_codes[i]
                        amount = option.dailyinfo.loc[tday, 'Amount' + str(i + 1)]  # 删除多余的*2
                        product_assets[asset_code] = amount
                    product_results[product_name] = product_assets
                else:
                    # 非小雪球：汇总amount
                    for i in range(0, option.asset_num):
                        if option.future_codes[i] not in asset_list:
                            asset_list[option.future_codes[i]] = option.dailyinfo.loc[tday, 'Amount' + str(i + 1)]  # 删除多余的*2
                        else:
                            asset_list[option.future_codes[i]] += option.dailyinfo.loc[tday, 'Amount' + str(i + 1)]
                
                end_time = time()
                print(f'完成 ({end_time - start_time:.1f}s)')
            else:
                print('未发行，跳过')
        except Exception as e:
            print(f'失败: {e}')
            continue
    
    if data_type_name == "小雪球":
        return product_results
    else:
        return asset_list

def main():
    """主函数 - 小雪球逐个列出，非小雪球汇总"""
    print('开始运行无delta_zbx依赖版本...')
    begin_time = time()
    
    # 1. 生成数据（内存中）
    print("正在提取产品数据...")
    snowball_data, other_data = create_element_summary_data()
    print(f"提取完成：小雪球产品 {len(snowball_data)} 个，其他产品 {len(other_data)} 个")
    
    # 2. 保存Excel文件
    print("正在保存Excel文件...")
    save_excel_files(snowball_data, other_data)
    print("Excel文件保存完成")
    
    # 3. 分别对两类产品进行估值
    
    # 处理小雪球（返回每个产品的详细数据）
    snowball_assets = {}
    if snowball_data:
        snowball_assets = run_estimation_on_data(snowball_data, "小雪球")
    
    # 处理其他产品（返回汇总数据）
    other_assets = {}
    if other_data:
        other_assets = run_estimation_on_data(other_data, "非小雪球")
    
    # 4. 分开输出结果
    print("\n" + "="*60)
    print("小雪球产品 - 逐个列出（不汇总）:")
    print("="*60)
    if snowball_assets:
        for product_name, product_data in snowball_assets.items():
            print(f"\n产品: {product_name}")
            for asset, amount in product_data.items():
                print(f"  {asset:18s}: {amount:12.2f}")
    else:
        print("无小雪球产品")
    
    print("\n" + "="*60)
    print("非小雪球产品 - 汇总amount:")
    print("="*60)
    if other_assets:
        for asset, amount in other_assets.items():
            print(f"{asset:20s}: {amount:12.2f}")
    else:
        print("无非小雪球产品")
    
    # 5. 计算总计（小雪球需要先汇总）
    all_assets = {}
    
    # 汇总小雪球的amount
    if snowball_assets:
        for product_name, product_data in snowball_assets.items():
            for k, v in product_data.items():
                all_assets[k] = all_assets.get(k, 0) + v
    
    # 加上非小雪球的amount
    for k, v in other_assets.items():
        all_assets[k] = all_assets.get(k, 0) + v
    
    print("\n" + "*"*40)
    print("标的资产amount")
    print(all_assets)
    
    # 提取主力合约
    zlhy_list = {}
    for ast in all_assets.keys():
        try:
            if ast in ['CGBFRI10.CCI', 'CBA00652.CS', 'T.CFE']:
                temp = w.wset("indexconstituent", "windcode=TFI.WI").Data
            else:
                temp = w.wset("indexconstituent", "windcode=" + ast).Data
            weight = np.array(temp[3])
            weight[weight == None] = 0
            zlhy = temp[1][weight.argmax()]
            if zlhy not in zlhy_list:
                zlhy_list[zlhy] = all_assets[ast]
            else:
                zlhy_list[zlhy] += all_assets[ast]
        except:
            continue
    
    print("*" * 40)
    print("主力合约amount")
    print(zlhy_list)
    
    end_time = time()
    run_time = end_time - begin_time
    print(f'\n总运行时间: {run_time:.1f}秒')

if __name__ == '__main__':
    main()