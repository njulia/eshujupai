from talib.abstract import *
import pandas as pd
import numpy as np


# 158 indicators
INIDCATORS = ['HT_DCPERIOD', 'HT_DCPHASE', 'HT_PHASOR', 'HT_SINE', 'HT_TRENDMODE', 'ADD', 'DIV', 'MAX', 'MAXINDEX', 'MIN', 'MININDEX',
 'MINMAX', 'MINMAXINDEX', 'MULT', 'SUB', 'SUM', 'ACOS', 'ASIN', 'ATAN', 'CEIL', 'COS', 'COSH', 'EXP', 'FLOOR', 'LN', 'LOG10',
 'SIN', 'SINH', 'SQRT', 'TAN', 'TANH', 'ADX', 'ADXR', 'APO', 'AROON', 'AROONOSC', 'BOP', 'CCI', 'CMO', 'DX', 'MACD', 'MACDEXT',
 'MACDFIX', 'MFI', 'MINUS_DI', 'MINUS_DM', 'MOM', 'PLUS_DI', 'PLUS_DM', 'PPO', 'ROC', 'ROCP', 'ROCR', 'ROCR100', 'RSI', 'STOCH',
 'STOCHF', 'STOCHRSI', 'TRIX', 'ULTOSC', 'WILLR', 'BBANDS', 'DEMA', 'EMA', 'HT_TRENDLINE', 'KAMA', 'MA', 'MAMA', 'MAVP', 'MIDPOINT',
 'MIDPRICE', 'SAR', 'SAREXT', 'SMA', 'T3', 'TEMA', 'TRIMA', 'WMA', 'CDL2CROWS', 'CDL3BLACKCROWS', 'CDL3INSIDE', 'CDL3LINESTRIKE',
 'CDL3OUTSIDE', 'CDL3STARSINSOUTH', 'CDL3WHITESOLDIERS', 'CDLABANDONEDBABY', 'CDLADVANCEBLOCK', 'CDLBELTHOLD', 'CDLBREAKAWAY',
 'CDLCLOSINGMARUBOZU', 'CDLCONCEALBABYSWALL', 'CDLCOUNTERATTACK', 'CDLDARKCLOUDCOVER', 'CDLDOJI', 'CDLDOJISTAR', 'CDLDRAGONFLYDOJI',
 'CDLENGULFING', 'CDLEVENINGDOJISTAR', 'CDLEVENINGSTAR', 'CDLGAPSIDESIDEWHITE', 'CDLGRAVESTONEDOJI', 'CDLHAMMER', 'CDLHANGINGMAN',
 'CDLHARAMI', 'CDLHARAMICROSS', 'CDLHIGHWAVE', 'CDLHIKKAKE', 'CDLHIKKAKEMOD', 'CDLHOMINGPIGEON', 'CDLIDENTICAL3CROWS', 'CDLINNECK',
 'CDLINVERTEDHAMMER', 'CDLKICKING', 'CDLKICKINGBYLENGTH', 'CDLLADDERBOTTOM', 'CDLLONGLEGGEDDOJI', 'CDLLONGLINE', 'CDLMARUBOZU',
 'CDLMATCHINGLOW', 'CDLMATHOLD', 'CDLMORNINGDOJISTAR', 'CDLMORNINGSTAR', 'CDLONNECK', 'CDLPIERCING', 'CDLRICKSHAWMAN',
 'CDLRISEFALL3METHODS', 'CDLSEPARATINGLINES', 'CDLSHOOTINGSTAR', 'CDLSHORTLINE', 'CDLSPINNINGTOP', 'CDLSTALLEDPATTERN',
 'CDLSTICKSANDWICH', 'CDLTAKURI', 'CDLTASUKIGAP', 'CDLTHRUSTING', 'CDLTRISTAR', 'CDLUNIQUE3RIVER', 'CDLUPSIDEGAP2CROWS',
 'CDLXSIDEGAP3METHODS', 'AVGPRICE', 'MEDPRICE', 'TYPPRICE', 'WCLPRICE', 'BETA', 'CORREL', 'LINEARREG', 'LINEARREG_ANGLE',
 'LINEARREG_INTERCEPT', 'LINEARREG_SLOPE', 'STDDEV', 'TSF', 'VAR', 'ATR', 'NATR', 'TRANGE', 'AD', 'ADOSC', 'OBV']

CORE_INDICATORS = ['ADX', 'ATR', 'BBANDS', 'CCI', 'MACD', 'ROC', 'RSI', 'STOCH', 'STOCHRSI', 'ULTOSC',  'WILLR']
# RSI(14) 	45.547 	Neutral
# STOCH(9,6) 	67.886 	Buy
# STOCHRSI(14) 	60.816 	Buy
# MACD(12,26) 	-0.620 	Sell
# ADX(14) 	27.461 	Sell
# Williams %R 	-45.545 	Neutral
# CCI(14) 	-3.5598 	Neutral
# ATR(14) 	2.4929 	High Volatility
# Highs/Lows(14) 	0.0000 	Neutral
# Ultimate Oscillator 	50.200 	Neutral
# ROC 	-0.057 	Sell
# Bull/Bear Power(13) 	-1.6800 	Sell

def _common_signal(indicator, upper_band=0.0, lower_band=0.0):
    if indicator > upper_band:
        return 1
    elif indicator < lower_band:
        return -1
    return 0

def _bband_signal(row):
    if (row['close'] > row['middleband']) and (row['bbandhist'] > 0):
        return 1
    elif (row['close'] < row['middleband']) and (row['bbandhist'] > 0):
        return -1
    return 0

def _bband_ext_signal(row):
    # Approch the 'upperband'
    if (row['upperband'] - row['close']) < (row['close'] - row['middleband']):
        return 1
    # Approach the 'lowerband'
    elif (row['close'] - row['lowerband']) < (row['middleband'] - row['close']):
        return -1
    return 0

def _adx_di_signal(row):
    if (row['plus_di'] > row['minus_di']) and (row['adx'] > 25):
        return 1
    elif (row['minus_di'] > row['plus_di']) and (row['adx'] > 25):
        return -1
    return 0

def _adx_dm_signal(row):
    if (row['plus_dm'] > row['minus_dm']) and (row['adx'] > 25):
        return 1
    elif (row['minus_dm'] > row['plus_dm']) and (row['adx'] > 25):
        return -1
    return 0

def _adx_di_ext_signal(row):
    if (row['plus_di'] > row['minus_di']) and (row['adx'] > row['minus_di']):
        return 1
    elif (row['minus_di'] > row['plus_di']) and (row['adx'] > row['plus_di']):
        return -1
    return 0

def _adx_dm_ext_signal(row):
    if (row['plus_dm'] > row['minus_dm']) and (row['adx'] > row['minus_dm']):
        return 1
    elif (row['minus_dm'] > row['plus_dm']) and (row['adx'] > row['plus_dm']):
        return -1
    return 0

def _adxr_di_signal(row):
    if (row['plus_di'] > row['minus_di']) and (row['adxr'] > row['minus_di']):
        return 1
    elif (row['minus_di'] > row['plus_di']) and (row['adxr'] > row['plus_di']):
        return -1
    return 0

def _adxr_dm_signal(row):
    if (row['plus_dm'] > row['minus_dm']) and (row['adxr'] > row['minus_dm']):
        return 1
    elif (row['minus_dm'] > row['plus_dm']) and (row['adxr'] > row['plus_dm']):
        return -1
    return 0

def _roc_signal(row):
    if (row['roc_125'] > 0) and (row['roc_21'] < -8) and (row['close'] > row['sma_20']):
        return 1
    elif (row['roc_125'] < 0) and (row['roc_21'] > 8) and (row['close'] < row['sma_20']):
        return -1
    return 0

def _rsi_ext_signal(row):
    if (row['rsi'] > 70) and (row['close'] > row['ema_20']):
        return 1
    if (row['rsi'] < 30) and (row['close'] < row['ema_20']):
        return -1
    return 0

def cal_technical_indicators(df=None):
    '''
    Convert pandas Dataframe to a dict with ndarray, then calculate the techinical indicators
    {'open': ndarray, 'close': ndarray, 'high': ndarray, 'low': ndarray, 'volume': ndarray}
    :param df: pandas DataFrame
    :return: pandas DataFrame enriched with technical indicators
    '''
    # Convert
    input ={c: df[c].values for c in df.columns}

    cal_overlap_studies(df, input)
    cal_momentum_indicators(df, input)
    cal_hybrid_indicators(df, input)

def cal_overlap_studies(df, input):
    '''
    Overlap Studies Functions
    '''
    # BBANDS: Bollinger Band
    # print(Function('BBANDS'))
    df['upperband'], df['middleband'], df['lowerband'] = BBANDS(input, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
    df['bbanddeviation'] = df['upperband'] - df['middleband']
    df['bbandhist'] = df['bbanddeviation'] - df['bbanddeviation'].ewm(span=20).mean()
    df['BBANDS_signal'] = df.apply(_bband_signal, axis=1)
    df['BBANDS_EXT_signal'] = df.apply(_bband_ext_signal, axis=1)

    # DEMA: Double Exponential Moving Average
    df['dema_5'] = DEMA(input, timeperiod=5)
    df['dema_20'] = DEMA(input, timeperiod=20)
    df['dema_50'] = DEMA(input, timeperiod=50)
    df['DEMA_signal'] = (df['close'] - df['dema_5']).apply(_common_signal)
    df['DEMA_EXT5_signal'] = (df['dema_5'] - df['dema_20']).apply(_common_signal)
    df['DEMA_EXT20_signal'] = (df['dema_20'] - df['dema_50']).apply(_common_signal)

    # EMA: Exponential Moving Average
    df['ema_5'] = EMA(input, timeperiod=5)
    df['ema_20'] = EMA(input, timeperiod=20)
    df['ema_50'] = EMA(input, timeperiod=50)
    df['EMA_signal'] = (df['close'] - df['ema_5']).apply(_common_signal)
    df['EMA_EXT5_signal'] = (df['ema_5'] - df['ema_20']).apply(_common_signal)
    df['EMA_EXT20_signal'] = (df['ema_20'] - df['ema_50']).apply(_common_signal)

    # MA: Moving Average
    df['ma_5'] = MA(input, timeperiod=5)
    df['ma_20'] = MA(input, timeperiod=20)
    df['ma_50'] = MA(input, timeperiod=50)
    df['MA_signal'] = (df['close'] - df['ma_5']).apply(_common_signal)
    df['MA_EXT5_signal'] = (df['ma_5'] - df['ma_20']).apply(_common_signal)
    df['MA_EXT20_signal'] = (df['ma_20'] - df['ma_50']).apply(_common_signal)

    # MAMA: MESA Adaptive Moving Average
    df['mama'], df['fama'] = MAMA(input, fastlimit=0.9, slowlimit=0.1)
    df['MAMA_signal'] = (df['mama'] - df['fama']).apply(_common_signal)

    # # MAVP: Moving average with variable period
    # df['mavp_5'] = MAVP(input, periods=5, minperiod=2, maxperiod=50, matype=0)
    # df['mavp_20'] = MAVP(input, periods=20, minperiod=2, maxperiod=50, matype=0)
    # df['mavp_50'] = MAVP(input, periods=50, minperiod=2, maxperiod=50, matype=0)
    # df['MAVP_signal'] = (df['close'] - df['mavp_5']).apply(_common_signal)
    # df['MAVP_EXT5_signal'] = (df['mavp_5'] - df['mavp_20']).apply(_common_signal)
    # df['MAVP_EXT20_signal'] = (df['mavp_20'] - df['mavp_50']).apply(_common_signal)

    # SMA: Simple Moving Average
    df['sma_5'] = SMA(input, timeperiod=5)
    df['sma_20'] = SMA(input, timeperiod=20)
    df['sma_50'] = SMA(input, timeperiod=50)
    df['SMA_signal'] = (df['close'] - df['sma_5']).apply(_common_signal)
    df['SMA_EXT5_signal'] = (df['sma_5'] - df['sma_20']).apply(_common_signal)
    df['SMA_EXT20_signal'] = (df['sma_20'] - df['sma_50']).apply(_common_signal)

    # T3: Triple Exponential Moving Average(T3)
    df['t3_5'] = T3(input, timeperiod=5, vfactor=0.5)
    df['t3_20'] = T3(input, timeperiod=20)
    df['t3_50'] = T3(input, timeperiod=50)
    df['T3_signal'] = (df['close'] - df['t3_5']).apply(_common_signal)
    df['T3_EXT5_signal'] = (df['t3_5'] - df['t3_20']).apply(_common_signal)
    df['T3_EXT20_signal'] = (df['t3_20'] - df['t3_50']).apply(_common_signal)

    # TEMA: Triple Exponential Moving Average
    df['tema_5'] = TEMA(input, timeperiod=5)
    df['tema_20'] = EMA(input, timeperiod=20)
    df['tema_50'] = EMA(input, timeperiod=50)
    df['TMA_signal'] = (df['close'] - df['tema_5']).apply(_common_signal)
    df['TEMA_EXT5_signal'] = (df['tema_5'] - df['tema_20']).apply(_common_signal)
    df['TEMA_EXT20_signal'] = (df['tema_20'] - df['tema_50']).apply(_common_signal)

    # TRIMA: Triangular Moving Average
    df['trima_5'] = TRIMA(input, timeperiod=5)
    df['trima_20'] = TRIMA(input, timeperiod=20)
    df['trima_50'] = TRIMA(input, timeperiod=50)
    df['TRIMA_signal'] = (df['close'] - df['trima_5']).apply(_common_signal)
    df['TRIMA_EXT5_signal'] = (df['trima_5'] - df['trima_20']).apply(_common_signal)
    df['TRIMA_EXT20_signal'] = (df['trima_20'] - df['trima_50']).apply(_common_signal)

    # WMA: Weighted Moving Average
    df['wma_5'] = WMA(input, timeperiod=5)
    df['wma_20'] = WMA(input, timeperiod=20)
    df['wma_50'] = WMA(input, timeperiod=50)
    df['WMA_signal'] = (df['close'] - df['wma_5']).apply(_common_signal)
    df['WMA_EXT5_signal'] = (df['wma_5'] - df['wma_20']).apply(_common_signal)
    df['WMA_EXT20_signal'] = (df['wma_20'] - df['wma_50']).apply(_common_signal)

def cal_momentum_indicators(df, input):
    '''
    Momentum Indicator Functions
    '''
    # ['ADX', 'ADXR', 'MINUS_DI', 'PLUS_DI', 'MINUS_DM', 'PLUS_DM', 'ATR', 'BBANDS', 'CCI', 'MACD', 'ROC', 'RSI', 'STOCH', 'STOCHRSI', 'ULTOSC', 'WILLR']

    # ADX: Average Directional Movement Index
    # ADXR: Average Directional Movement Index Rating
    # MINUS_DI: Minus Directional Indicator
    # MINUS_DM: Minus Directional Movement
    # PLUS_DI: Plus Directional Indicator
    # PLUS_DM: Plus Directional Movement
    df['adx'] = ADX(input, timeperiod=14)
    df['adxr'] = ADXR(input, timeperiod=14)
    df['minus_di'] = MINUS_DI(input, timeperiod=14)
    df['minus_dm'] = MINUS_DM(input, timeperiod=14)
    df['plus_di'] = PLUS_DI(input, timeperiod=14)
    df['plus_dm'] = PLUS_DM(input, timeperiod=14)
    df['ADX_DI_signal'] = df.apply(_adx_di_signal, axis=1)
    df['ADX_DM_signal'] = df.apply(_adx_dm_signal, axis=1)
    df['ADX_DI_EXT_signal'] = df.apply(_adx_di_signal, axis=1)
    df['ADX_DM_EXT_signal'] = df.apply(_adx_dm_signal, axis=1)
    df['ADXR_DI_signal'] = df.apply(_adxr_di_signal, axis=1)
    df['ADXR_DM_signal'] = df.apply(_adxr_dm_signal, axis=1)

    # APO: Absolute Price Oscillator
    df['apo'] = APO(input, fastperiod=12, slowperiod=26, matype=0)
    df['APO_signal'] = df['apo'].apply(_common_signal)

    # AROON: Aroon
    df['aroondown'], df['aroonup'] = AROON(input, timeperiod=14)
    df['AROON_signal'] = (df['aroonup'] - df['aroondown']).apply(_common_signal)

    # AROONOSC: Aroon Oscillator
    df['aroonosc'] = AROONOSC(input, timeperiod=25)
    df['AROONOSC_signal'] = df['aroonosc'].apply(_common_signal)

    # BOP: Balance Of Power
    df['bop'] = BOP(input)
    df['BOP_signal'] = df['bop'].apply(_common_signal)

    # ATR: Average True Range


    # CCI: Commodity Channel Index
    df['cci'] = CCI(input, timeperiod=14)
    df['CCI_signal'] = df['cci'].apply(_common_signal, args=(100, -100))

    # CMO: Chande Momentum Oscillator
    df['cmo'] = CMO(input, timeperiod=20)
    df['CMO_signal'] = df['cmo'].apply(_common_signal, args=(20, -20))

    # DX: Directional Movement Index
    df['dx'] = DX(input, timeperiod=14)

    # MACD: Moving Average Convergence / Divergence
    # Buy when macdhist > 0 ; Sell when macdhist < 0
    df['macd'], df['macdsignal'], df['macdhist'] = MACD(input, fastperiod=12, sLowperiod=26, signalperiod=9)
    df['MACD_signal'] = df['macdhist'].apply(_common_signal)
    df['MACD_EXT_signal'] = df['macd'].apply(_common_signal)

    # MACDEXT: MACD with controllable MA type
    df['macd_ext'], df['macdsignal_ext'], df['macdhist_ext'] = MACDEXT(input, fastperiod=12, fastmatype=0, slowperiod=26, slowmatype=0,
                                         signalperiod=9, signalmatype=0)
    df['MACDEXT_signal'] = df['macdhist_ext'].apply(_common_signal)
    df['MACDEXT_EXT_signal'] = df['macd_ext'].apply(_common_signal)

    # MACDFIX: Moving Average Convergence/Divergence Fix 12/26
    df['macd_fix'], df['macdsignal_fix'], df['macdhist_fix'] = MACDFIX(input, signalperiod=9)
    df['MACDFIX_signal'] = df['macdhist_fix'].apply(_common_signal)
    df['MACDFIX_EXT_signal'] = df['macd_fix'].apply(_common_signal)

    # # MFI: Money Flow Index
    # df['mfi'] = MFI(input, timeperiod=14)
    # df['MFI'] = df['mfi'].apply(_common_signal, 70, 30)

    # MOM: Momentum
    df['mom'] = MOM(input, timeperiod=10)
    df['MOM_signal'] = df['mom'].apply(_common_signal)

    # PPO: Percentage Price Oscillator
    df['ppo'] = PPO(input, fastperiod=12, slowperiod=26, matype=0)
    df['PPO_signal'] = df['ppo'].apply(_common_signal)

    # ROC: Rate of change : ((price/prevPrice)-1)*100
    # https://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:rate_of_change_roc_and_momentum
    df['roc_125'] = ROC(input, timeperiod=125)
    df['roc_21'] = ROC(input, timeperiod=21)
    df['ROC_signal'] = df.apply(_roc_signal, axis=1)

    # ROCP: Rate of change Percentage: (price-prevPrice)/prevPrice
    df['rocp'] = ROCP(input, timeperiod=10)

    # ROCR: Rate of change ratio: (price/prevPrice)
    df['rocp'] = ROCR(input, timeperiod=10)

    # ROCR100: Rate of change ratio 100 scale: (price/prevPrice)*100
    df['rocp100'] = ROCR100(input, timeperiod=10)

    # RSI: Relative Strength Index
    df['rsi'] = RSI(input, timeperiod=14)
    df['RSI_signal'] = df['rsi'].apply(_common_signal, args=(70, 30))
    df['RSI_EXT_signal'] = df.apply(_rsi_ext_signal, axis=1)

    # STOCH: Stochastic
    df['slowk'], df['slowd'] = STOCH(input, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)

    # STOCHF: Stochastic Fast
    df['fastk'], df['fastd'] = STOCHF(input, fastk_period=5, fastd_period=3, fastd_matype=0)

    # STOCHRSI: Stochastic Relative Strength Index
    df['fastk_ext'], df['fastd_ext'] = STOCHRSI(input, timeperiod=14, fastk_period=5, fastd_period=3, fastd_matype=0)

    # TRIX: 1-day Rate-Of-Change (ROC) of a Triple Smooth EMA
    df['trix'] = TRIX(input, timeperiod=30)

    # ULTOSC: Ultimate Oscillator
    df['ultosc'] = ULTOSC(input, timeperiod1=7, timeperiod2=14, timeperiod3=28)

    # WILLR: Williams' %R
    df['willr'] = WILLR(input, timeperiod=14)
    df['WILLR_signal'] = df['willr'].apply(_common_signal, args=(-20, -80))
    df['WILLREXT_signal'] = df['willr'].apply(_common_signal, args=(-50, -50))

def cal_hybrid_indicators(df, input):
    df['HYBRID1_signal'] = (df['MACD_signal'] + df['BBANDS_signal']).apply(_common_signal, args=(1, -1))
    df['HYBRID2_signal'] = (df['MACD_signal'] + df['WILLREXT_signal']).apply(_common_signal, args=(1, -1))
    df['HYBRID3_signal'] = (df['MA_signal'] + df['BBANDS_signal']).apply(_common_signal, args=(1, -1))
    df['HYBRID4_signal'] = (df['MA_signal'] + df['MACD_signal']).apply(_common_signal, args=(1, -1))
    df['HYBRID5_signal'] = (df['MA_signal'] + df['WILLREXT_signal']).apply(_common_signal, args=(1, -1))

if __name__ == '__main__':
    df = pd.DataFrame({
        'open': np.random.random(100),
        'high': np.random.random(100),
        'low': np.random.random(100),
        'close': np.random.random(100),
        'volume': np.random.random(100)
    })

    cal_technical_indicators(df)