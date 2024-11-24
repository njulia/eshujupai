from web.settings import BASE_DIR
from predict.run import read_data_from_feed
from predictapp.models import Security
import os
import numpy as np


def calc_stats(ticker):
    '''
    Weekly and monthly change statistics
    :param df: pandas dataframe with columns 'close', 'open', 'high', 'low'
    :return:
    '''
    print(f'----------------{ticker}----------------')
    df = read_data_from_feed(ticker, days=1000)

    # Daily stats
    close_diff = abs(df['close'] - df['open'])
    print('Daily CLOSE stats: ', close_diff.describe())
    df['daily_diff'] = df['high'] - df['low']
    print('Daily HIGH-LOW stats: ', df['daily_diff'].describe())

    # Weekly stats
    close_max = df['close'].resample('W', label='right', closed='right').max()
    close_min = df['close'].resample('W', label='right', closed='right').min()
    close_diff = close_max - close_min
    print('Weekly CLOSE stats: ', close_diff.describe())
    high_max = df['high'].resample('W', label='right', closed='right').max()
    low_min = df['low'].resample('W', label='right', closed='right').min()
    df['weekly_diff'] = high_max - low_min
    print('Weekly HIGH-LOW stats: ', df['weekly_diff'].describe())

    # Monthly stats
    close_max = df['close'].resample('M', label='right', closed='right').max()
    close_min = df['close'].resample('M', label='right', closed='right').min()
    close_diff = close_max - close_min
    print('Monthly CLOSE stats: ', close_diff.describe())
    high_max = df['high'].resample('M', label='right', closed='right').max()
    low_min = df['low'].resample('M', label='right', closed='right').min()
    df['monthly_diff'] = high_max - low_min
    print('Monthly HIGH-LOW stats: ', df['monthly_diff'].describe())

    # Save data to /documents
    df.to_csv(os.path.join(BASE_DIR, f'documents/{ticker}_stats.csv'))

def zhangting_scanner(exchanges=[], tickers=None):
    '''
    Check if 2 continuous 涨停, whether the 3rd day 涨停
    :param exchanges:
    :param tickers:
    :return:
    '''
    def _scanner(row, ticker):
        '''
        Check how many 2 continuous 涨停 and 3 continuous 涨停
        :param row: pandas row
        :return: zt_2=1 if 2 continuous 涨停, zt_3 if 3 continuous 涨停, else 0
        '''
        zt_2, zt_3 = 0, 0
        if row['zhangting_1'] > 0 and row['zhangting_2'] > 0:
            zt_2 = 1
            print(f'addd-zhangting_scanner: {ticker} 2 zhangting')
            if ['zhangting'] > 0:
                zt_3 = 1
                print(f'addd-zhangting_scanner: {ticker} 3 zhangting')
        return zt_3

    if not tickers:
        kwargs = {}
        if exchanges:
            kwargs['exchange__in'] = exchanges
        tickers = Security.objects.filter(**kwargs).values_list('ticker', flat=True)

    for ticker in tickers:
        try:
            print(f'addd-zhangting_scanner: {ticker}')
            df = read_data_from_feed(ticker, days=1000)
            df['change'] = df['close']/df['open']
            df['zhangting'] = np.where(df['change'] > 1.09, 1, 0)
            df['zhangting_1'] = df['zhangting'].shift(1)
            df['zhangting_2'] = df['zhangting_1'].shift(1)
            df['zt_3'] = df.apply(_scanner, axis=1, args=(ticker,))
            # print(f'addd-zhangting_scanner: {zt_2}, {type(zt_2)}')
            # print(f'addd-zhangting_scanner: {zt_3}, {type(zt_3)}')
            df.to_csv(os.path.join(BASE_DIR,  f'documents/{ticker}_zt.csv'))
        except:
            continue



