import tushare as ts
import datetime as dt
import time
import typing
import sys
import os

import matplotlib.pyplot as plt
import mpl_finance as mpf
import numpy as np

sys.path.append('..\..')
from Helper import DrawHelper
from Helper import ZipHelper

""""
# 寻找反转模式
# 1. ma10 连续在 ma20下 n 天后，首次出现交叉，获取这样的区间数据（不包含交叉当天）
# 2. 在交叉日区间中，找到最低点对应的日期
# 3. 从最低点向前取 m 个交易日
# 4. 记录股票代码、日期区间、价格区间，输出区间数据的图像

# 后续改进：
# 1.在交叉区间内，找到最低点对应日期，向后取 m 个交易日
# 2.若最低点后的 m 个交易日涨幅达到x，即为所求 
# or
# 1.在交叉日期后，向后取 m 个交易日
# 2.若连续 m 天 ma10 > ma20，即为所求
"""

# 获取所有股票列表
def GetAllStockList():
    pro = ts.pro_api('6d9ac99d25b0157dcbb1ee3d35ef1250e5295ff80bb59741e1a56b35')
    df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol')
    allstocklistdic = dict()
    allstocklistdic1 = dict()
    for col in df.values:
        allstocklistdic[col[0]] = col[1]
        allstocklistdic1[col[1]] = col[0]
    return allstocklistdic

# 获取股票池，结构{symbol:bool}
def GetStockPool(indexCode='399300.SZ'):
    pro = ts.pro_api('1c5440f527d1e513c75d10518ef9fd05a34a33ec4146b353bc7ce5bf')
    # 月初月末各公布一次成分股
    startdate = (dt.datetime.today() - dt.timedelta(31)).strftime("%Y%m%d")
    df = pro.index_weight(index_code=indexCode, start_date=startdate, end_date=time.strftime("%Y%m%d"))
    stockPoolDic = dict()
    for col in df.values:
        stockPoolDic[col[1]] = True
    return list(stockPoolDic.keys())

# 取股票均线数据
# maPara: 想要获取的均线窗口值
def GetStockMA(stockCode, period=1401, maPara=[10, 20], calDay=100, type="D", benchmark="close"):
    startdate = (dt.datetime.today() - dt.timedelta(period)).strftime("%Y%m%d")
    df = ts.pro_bar(ts_code=stockCode, adj='qfq', start_date=startdate, end_date=time.strftime("%Y%m%d"), ma=maPara)
    
    # 样本点小于40个不计算
    if df is None or df.values is None or len(df.values) < 40:
        print("数据缺失：",stockCode)
        return False
    
    # 遍历重构正向时序上的数据
    OrderDic = typing.OrderedDict()
    for i in range(len(df.values)-1,-1,-1):
        # 剔除前n天均线为Nan值的数据
        if i > len(df.values) - maPara[len(maPara)-1]:
            continue
        value = df.values[i]
        OrderDic[value[1]] = {'tdate':value[1], 'open':value[2], 'high':value[3], 'low':value[4], 'close':value[5], \
            'lclose':value[6], 'change':value[7], 'chg':value[8], 'vol':value[9], 'amount':value[10]*1000, \
            'ma10':value[11], 'ma_v_10':value[12], 'ma20':value[13], 'ma_v_20':value[14]}
    #print(OrderDic[next(reversed(OrderDic))])
    return OrderDic

# 判断反转模式
def FindReversal(stockMA, reversalDay=8):
    # 连续趋势计数
    compareCount = 0
    # 日期列表
    seriesTdateList = list()
    # 交易数据列表
    seriesList = list()
    OrderDic = typing.OrderedDict()
    for stockMAKey, stockMAValue in stockMA.items():
        # 从首次下跌趋势开始时，记录本次趋势内序列
        if float(stockMAValue["ma10"]) <= float(stockMAValue["ma20"]):
            seriesTdateList.append(stockMAValue["tdate"])
            seriesList.append([stockMAValue["open"],stockMAValue["high"],stockMAValue["low"],stockMAValue["close"]])
            compareCount += 1
        # 遇到死叉本轮趋势终止，若本轮下跌趋势满足趋势时长，在OrderDic添加本轮趋势序列（默认不记录死叉当天信息，若记录死叉当天信息，在此处添加即可）
        if float(stockMAValue["ma10"]) > float(stockMAValue["ma20"]):
            if compareCount > reversalDay:
                # 寻找区间最低点的位置
                featureList = np.array(seriesList)[:,3].tolist()
                featureList.reverse()
                minIndex = featureList.index(min(featureList))
                theIndex = len(featureList)-minIndex-1
                #featureList.reverse()
                # 只存储最低点之前的序列
                OrderDic[stockMAValue["tdate"]] = {"tdateList":seriesTdateList[:theIndex+1], "seriesList":seriesList[:theIndex+1]}
            seriesTdateList = list()
            seriesList = list()
            compareCount = 0
    return OrderDic

# 画出每个符合要求的图
def SavePicture(code, dataDic, reversalDay, reversalDayOffset, dirPath=''):
    if dirPath == '' or not os.path.exists(dirPath):
        dirPath = sys.path[0]
        print("缺少保存路径，默认保存至当前文件夹下")
    for item in dataDic.values():
        if len(item["tdateList"]) > reversalDay - reversalDayOffset:
            tdateList = item["tdateList"][-reversalDay+reversalDayOffset:]
            priceList = item["seriesList"][-reversalDay+reversalDayOffset:]
            path = dirPath + "\\" + code + "_" + item["tdateList"][0] + ".png"
            DrawHelper.DrawDataK(tdateList, priceList, path)
        else:
            print(code,":数据量不足","，不生成图片")

# 主函数
if __name__ == '__main__':
    # 生成策略结果数据
    tagDic = dict()
    # 循环计数器
    dataCount = 0
    # 股票样本大小限制
    sampleCount = 50
    # 提取趋势区间序列长度
    reversalDay = 21
    # 提取趋势区间长度偏移量，剔除最低点右侧数据后，序列提取长度应相对缩短
    reversalDayOffset = 5
    # 压缩文件源路径
    dirPath = "..\\..\\..\\Communal\\ReversalPositive"
    # 压缩文件生成路径
    imgOutFullName = "..\\..\\..\\Communal\\ReversalPositive{0}.zip".format(time.strftime("%Y%m%d"))

    # 获取股票池 上证50:000016.SH 沪深300:399300.SZ 上证180：000010.SH
    stockPoolList = GetStockPool('000016.SH')
    # 读取全市场股票列表
    for code in GetAllStockList().keys():
        if len(stockPoolList) > 0 and code not in stockPoolList:
            continue
        # 获取均线数据
        stockMADic = GetStockMA(code)
        
        if dataCount > sampleCount:
            break
        elif stockMADic == False:
            continue
        else:
            # 找到反转模式区间
            reversalDic = FindReversal(stockMADic, reversalDay)
            # 生成反转模式区间的图片
            SavePicture(code, reversalDic, reversalDay, reversalDayOffset, dirPath)
            dataCount += 1
            if dataCount == 500:
                time.sleep(60)
    
    # 压缩生成图片的文件夹
    ZipHelper.ZipDir(dirPath, imgOutFullName)






    print("finish")
    input()
    reversalDic = 0
    # 返回用于作图的数据
    testOne = list(reversalDic.keys())[0]
    if len(reversalDic[testOne]["tdateList"]) > reversalDay - reversalDayOffset:
        DrawHelper.DrawDataK(reversalDic[testOne]["tdateList"][-reversalDay+reversalDayOffset:], reversalDic[testOne]["seriesList"][-reversalDay+reversalDayOffset:])
    else:
        pass


    # 画出每个符合要求的图
    for item in reversalDic.values():
        if len(item["tdateList"]) > reversalDay - reversalDayOffset:
            tdateList = item["tdateList"][-reversalDay+reversalDayOffset:]
            priceList = item["seriesList"][-reversalDay+reversalDayOffset:]
            path = "..\\..\\..\\Communal\\ReversalPicture\\"+item["tdateList"][0]+".png"
            DrawHelper.DrawDataK(tdateList, priceList, path)
        else:
            pass

    #DrawHelper.DrawDataK(reversalDic[listIndex[0]]["tdateList"], reversalDic[listIndex[0]]["seriesList"])


