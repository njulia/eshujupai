import pandas as pd
import numpy as np
from predict.settings import BACKTEST_INPUT_COLUMNS, BACKTEST_OUTPUT_COLUMNS, BACKTEST_SET, PRICE_COLUMNS
from utils.settings_index import indexes


def invalid(f):
    '''
    Check whether the price is valid or not
    :param f: float
    :return: True if invalid else False
    '''
    # print(f'addd-invalid: {f}, {type(f)}')
    if np.isnan(f) or np.isinf(f) or f < 1e-6 or not np.isfinite(f):
        return True
    return False

def preprocess(df):
    """
    Calculate the value of change, up_high, up_low and down_high, down_low.
    change = close - open
    If change >= 0, up_high = (high - open)/open, up_low= (low - open)/open
    If change <0, down_high = (high - open)/open, down_low = (low - open)/open
    :param df:
    :return: dataframe
    """
    # ML Features
    for index, row in df.iterrows():
        if invalid(row['high']) or invalid(row['low']) or invalid(row['open']) or invalid(row['close']):
                # or invalid(row['volume'])
            df.drop(index, axis=0, inplace=True)
    # As the close price is not the last price, use the next day's open as close price
    #df = df.rename(columns={'close': 'close_orig'})
    df['close_orig'] = df['close']
    df['close'] = df['open'].shift(-1)
    df['close'].iloc[-1] = df['close_orig'].iloc[-1]

    df['hc'] = df['high'] / df['close']
    df['lc'] = df['low'] / df['close']
    df['oc'] = df['open'] / df['close']
    df['close_change'] = df['close'].pct_change()
    #df['volume_change'] = df['volume'].pct_change()

    # df['close_change'] = np.where(np.isinf(df['close_change']), 0, df['close_change'])
    # df['volume_change'] = np.where(np.isinf(df['volume_change']), 0, df['volume_change'])

    # ML Target
    df['entry_price'] = df['open']
    df['change'] = np.where(df['close'] >= df['open'], 1, -1)
    df['signal'] = df['change'].shift(-1)
    df.fillna(0, inplace=True)


    # The ratio of high and low price to open price when df['change'] >= 0
    df['up_high'] = np.where(df['change']>=0, (df['high']-df['open'])/df['open'], np.nan)
    df['up_low'] = np.where(df['change']>=0, (df['low']-df['open'])/df['open'], np.nan)

    # The ratio of high and low price against open price when df['change'] < 0
    df.loc[df['change']<0, 'down_high'] = (df['high']-df['open'])/df['open']
    df['down_high'] = df['down_high'].fillna(np.nan)
    df.loc[df['change']<0, 'down_low'] = (df['low']-df['open'])/df['open']
    df['down_low'] = df['down_low'].fillna(np.nan)

    df['up_high_mean'] = df['up_high'].mean()   # >0
    df['up_low_mean'] = df['up_low'].mean()   # <0
    df['down_high_mean'] = df['down_high'].mean()   # >0
    df['down_low_mean'] = df['down_low'].mean()   # <0

    return df

def predict(df, signal_column, profit_factor, loss_factor):
    """
    Predicted whether to BUY or SELL next day, and the take_profit and stop_loss price
    :param df: dataframe including the 'close' price and the signal to buy or sell
    :param profit_factor: the factor to adjust the upper distance to reference_price
    :param loss_factor: the factor to adjust the lower distance to reference_price
    :return: integer: buy or sell signal ( 1: buy, -1: sell, 0: no signal)
             float: profit_take, 2 decimal
             float: loss_stop, 2 decimal
    """
    last_row = df.iloc[-1]
    signal = last_row[signal_column]
    close = last_row['close']
    profit_take = np.nan
    loss_stop = np.nan
    if signal > 0:
        # BUY
        profit_take = round(close * (1 + last_row['up_high_mean'] * profit_factor), 2)
        loss_stop = round(close * (1 + last_row['up_low_mean'] * loss_factor), 2)
    elif signal < 0:
        # SELL
        profit_take = round(close * (1 + last_row['down_low_mean'] * profit_factor), 2)
        loss_stop = round(close * (1 + last_row['down_high_mean'] * loss_factor), 2)
    return signal, close, profit_take, loss_stop

def cal_pnl(row, commission, signal_column, i, j, can_short=True):
    """
    Calculate the pnl when using the predicted 'signal' to BUY or SELL
    :param row: each row in the dataframe
    :param i: the factor to adjust the upper distance to reference_price
    :param j: the factor to adjust the lower distance to reference_price
    :param commission: commission
    :return: float, the pnl daily
    """
    reference_price = row['entry_price'] # Can use 'open' price as well. But cannot get the 'open' price before the market open if run the program after market closes.

    # Predict BUY
    if row[signal_column] > 0:
        # If the reference_price is not in the range [low, high], the order won't be filled
        if reference_price < row['low']:
            return 0
        if reference_price > row['open']:
            reference_price = row['open']

        # Take profit when increase to profit_bound. Stop loss when decrease to loss_bound
        profit_bound = reference_price * (1 + row['up_high_mean'] * i)   # >reference_price, profit take
        loss_bound = reference_price * (1 + row['up_low_mean'] * j)   # <reference_price, loss stop
        if loss_bound >= row['low']:
            # Stop loss, pnl<0
            # Close the LONG position, charge 2*commission as the commission has not been charged when open the position
            pnl = loss_bound - reference_price - 2*commission
        elif profit_bound <= row['high']:
            # Take profit, pnl>0
            # Close the LONG position, charge 2*commission as the commission has not been charged when open the position
            pnl = profit_bound - reference_price - 2*commission
        else:
            # todo: minus 2*commission when close the position, e.g., the signal next day is different with the LONG/SHORT posiition
            pnl = row['close'] - reference_price
        return pnl

    # Predict SELL. No short for Chinese stocks
    if row[signal_column] < 0 and can_short:
        # If the reference_price is not in the range [low, high], the order won't be filled
        if reference_price > row['high']:
            return 0
        if reference_price < row['open']:
            reference_price = row['open']

        # Stop loss when increase to loss_bound. Take profit when decrease to profit_bound
        loss_bound = reference_price * (1 + row['down_high_mean'] * j)   # >reference_price, loss stop
        profit_bound = reference_price * (1 + row['down_low_mean'] * i)   # <reference_price, profit take
        if loss_bound <= row['high']:
            # Stop loss, pnl<0
            # Close the SHORT position, charge 2*commission as the commission has not been charged when open the position
            pnl = reference_price - loss_bound - 2*commission
        elif profit_bound >= row['low']:
            # Take profit, pnl<0
            # Close the SHORT position, charge 2*commission as the commission has not been charged when open the position
            pnl = reference_price - profit_bound - 2*commission
        else:
            # todo: minus 2*commission when close the position, e.g., the signal next day is different with the LONG/SHORT posiition
            pnl = reference_price - row['close']
        return pnl

    # Don't BUY or SELL
    return 0

def backtest_factors(df, commission, signal_column, profit_factor, loss_factor, can_short=True):
    """
    :param df: dataframe
    :param commission: commission to buy/sell 1 share
    :param signal_column: the column which is used to decide whether to buy or sell
    :param profit_factor: the factor used to adjust the highest price for stop_loss or take_profit
    :param loss_factor: the factor used to adjust the lowest price for stop_loss or take_profit
    :return: dataframe enriched with 'pnl' and 'return' (accumlated return)
    """
    # Daily PnL
    df['pnl'] = df.apply(cal_pnl, axis=1, args=(commission, signal_column, profit_factor, loss_factor, can_short))
    df['return'] = df['pnl'].cumsum()
    return df

def backtest(df, commission, signal_column, strategy, can_short=True, ticker='', backtest_set=BACKTEST_SET):
    """
    :param df: dataframe
    :param commission: commission to buy/sell 1 share
    :param signal_column: the column which is used to decide whether to buy or sell
    :param strategy: strategy name, e.g., MACD
    :return: dataframe with return for different (profit_factor , loss_factor) pairs
    """
    result = pd.DataFrame(columns=BACKTEST_OUTPUT_COLUMNS)

    df['position'] = df[signal_column].shift(1)
    df.iat[0, -1] = 0
    df['position'].astype(int)
    df_backtest = df.iloc[-backtest_set:][BACKTEST_INPUT_COLUMNS]
    factors = (6, 3)
    step_profit = 0.5
    step_loss = 0.3
    if ticker in indexes['Favorite'].index_tickers:
        factors = (10, 4)
        step_profit = step_loss = 0.1
        # print(f'addd-backtest: {factors}')
    for profit_factor in np.arange(0.1, factors[0], step_profit):
        for loss_factor in np.arange(0.1, factors[1], step_loss):
            # Daily PnL
            backtest_factors(df_backtest, commission, 'position', profit_factor, loss_factor, can_short)
            # The total return for the whole tested duration
            return_total = round(df_backtest['return'].iloc[-1], 2)
            # The return rate for last BACKTEST_SET days
            return_rate = round(float(return_total) / df_backtest['open'].iloc[0] * 100.0, 2)
            sharpe = 0
            drawdown = 0
            volatility = 0

            predict_signal, predict_price, predict_take_profit, predict_stop_loss = predict(df, signal_column, profit_factor, loss_factor)
            # Dataframe columns: BACKTEST_OUTPUT_COLUMNS
            result.loc[len(result)] = [strategy, commission, profit_factor, loss_factor, return_total, return_rate,
                                       sharpe, drawdown, volatility, predict_signal, predict_price, predict_take_profit, predict_stop_loss]
            # path = os.path.join(BASE_DIR,  f'documents/zb_{profit_factor}_{loss_factor}.csv')
            # df_backtest.to_csv(path)

    print(f'addd-backtest: {strategy}')

    return result

def get_return(df, backtest_result, can_short, backtest_set=BACKTEST_SET):
    result = pd.DataFrame()
    result[PRICE_COLUMNS] = df.iloc[-backtest_set:][PRICE_COLUMNS]
    for row in backtest_result.itertuples():
        signal_column = '{0}_signal'.format(row.strategy)
        df['position'] = df[signal_column].shift(1)
        df.iat[0, -1] = 0
        df['position'].astype(int)
        df_backtest = df.iloc[-backtest_set:][BACKTEST_INPUT_COLUMNS]
        backtest_factors(df_backtest, row.commission, 'position', row.profit_factor, row.loss_factor, can_short)
        result[row.strategy] = df_backtest['return']
    return result