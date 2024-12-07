import json
import pandas as pd 
import numpy as np 

def getClosesFromKLINE(KLINE):

    data = json.dumps(KLINE)
    loader = json.loads(data)
    df = pd.DataFrame(loader)
    #df.columns = ['open_time',
                #  'o', 'h', 'l', 'c', 'v',
                #  'close_time', 'qav', 'num_trades',
                #  'taker_base_vol', 'taker_quote_vol', 'ignore']

    saucedUp = df.iloc[:,4]
    grabTestDataHere =  np.array(saucedUp)
    return grabTestDataHere.astype(float)


def getVolumesFromKLINE(KLINE):

    data = json.dumps(KLINE)
    loader = json.loads(data)
    df = pd.DataFrame(loader)
    #df.columns = ['open_time',
                #  'o', 'h', 'l', 'c', 'v',
                #  'close_time', 'qav', 'num_trades',
                #  'taker_base_vol', 'taker_quote_vol', 'ignore']

    saucedUp = df.iloc[:,5]
    grabTestDataHere =  np.array(saucedUp)
    return grabTestDataHere.astype(float)

def getLowsFromKLINE(KLINE):

    data = json.dumps(KLINE)
    loader = json.loads(data)
    df = pd.DataFrame(loader)
    #df.columns = ['open_time',
                #  'o', 'h', 'l', 'c', 'v',
                #  'close_time', 'qav', 'num_trades',
                #  'taker_base_vol', 'taker_quote_vol', 'ignore']

    saucedUp = df.iloc[:,3]
    grabTestDataHere =  np.array(saucedUp)
    return grabTestDataHere.astype(float)

def getHighsFromKLINE(KLINE):

    data = json.dumps(KLINE)
    loader = json.loads(data)
    df = pd.DataFrame(loader)
    #df.columns = ['open_time',
                #  'o', 'h', 'l', 'c', 'v',
                #  'close_time', 'qav', 'num_trades',
                #  'taker_base_vol', 'taker_quote_vol', 'ignore']

    saucedUp = df.iloc[:,2]
    grabTestDataHere =  np.array(saucedUp)
    return grabTestDataHere.astype(float)