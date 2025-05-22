# -*- coding: utf-8 -*-
"""挂钩资产库，其每日更新的数据用于判断是否敲出和计算估值"""

from WindPy import w
import pandas as pd
import sys

from indices import Indices

class Futures(Indices):
    def __init__(self, codes):
        super(Futures, self).__init__(codes)
        
