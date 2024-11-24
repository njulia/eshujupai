from django.core.files.uploadedfile import InMemoryUploadedFile
import pandas as pd
pd.core.common.is_list_like = pd.api.types.is_list_like
import pandas_datareader.data as source
import quandl
from tiingo import TiingoClient
from datetime import date, timedelta, datetime
from predict.process import preprocess, backtest, get_return
from predict.technical_indicators import cal_technical_indicators
from predict.ml.ml_indicator import cal_ml_indicators
from predict.settings import BACKTEST_SET, FEED_DAYS
from web.settings import TIINGO_API_KEY, BASE_DIR
import os
from threading import Thread
import logging
import traceback
# from predictapp.models_operation import (
#     delete_backtest,
#     get_backtest,
# )


log = logging.getLogger(__name__)

# Use 52 weeks historical data for backtest
_END_DATE = date.today()
# _START_DATE = _END_DATE - timedelta(days=120)
# _END_DATE = date(year=2019, month=4, day=4)
# _START_DATE = date(year=2018, month=10, day=5)


def _rename_strategy(row):
    return '{0}_{1}{2}'.format(row['strategy'], round(row['loss_factor']), round(row['profit_factor']))

def format_file_to_csv(file_path, ticker=None):
    with open(file_path, 'r') as f:
        old = f.read()
        if ticker in ('gold',):
            old = old.replace('\t1,', ',1')
        new = old.replace('\t', ',').replace(', 2021,', ' 2021,')

    with open(file_path, 'w') as f:
        f.write(new)

def read_data_from_file(file_path, period='D', ticker=None):
    try:
        format_file_to_csv(file_path, ticker)
        if isinstance(file_path, InMemoryUploadedFile):
            file_path.seek(0)
        df = pd.read_csv(file_path)
        # df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
        df.set_index('date', inplace=True)
        df.index = pd.DatetimeIndex(df.index)
        df.sort_index(ascending=True, inplace=True)
        log.info(f'Read data from file {file_path}: {len(df)}')
        # df.rename(columns={'Open':'open', 'Close':'close', 'High':'high', 'Low':'low', 'Volume':'volume'}, inplace=True)
        return resample_data(df, period)
    except:
        log.warn(traceback.print_exc())
        return None

def resample_data(df, period='D'):
    if period == 'D':
        return df
    df_sampled = df.resample(period, label='right', closed='right').agg(
        {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'})
    #df_sampled = df.resample(period, label='right', closed='right').agg(
    #    {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})
    return df_sampled

def read_data_from_feed(ticker, days=FEED_DAYS, period='D'):
    '''
    Get historical data from feeds
    :param ticker: string, ticker
    :param days: int, how many days of historical data
    :param period: string, the period of sampling, e.g, 'D': daily, 'W': weekly, 'M': monthly
    :return: DataFrame of historical data
    '''
    try:
        if period == 'W':
            days = 5*days
        elif period == 'M':
            days = 22*days

        if ticker in ('gold', 'us30', 'us10', 'us5'):
            # df = read_data_from_file(f'/home/julia/trading_analysis/web/documents/{ticker}.csv') # linux
            # return resample_data(df, period).iloc[-days:]
            return read_data_from_file(f'/Users/jingnie/startup/eshujupai/documents/{ticker}.csv', ticker=ticker, period=period) # mac
        if ticker.lower() == 'gold':
            # df = source.DataReader("WGC/GOLD_DAILY_USD", 'quandl', start=_END_DATE-timedelta(years=5), end=_END_DATE)
            df = quandl.get("CHRIS/CME_GC1", authtoken="U8PYFxxxZHMDnePH2w1t")
            df.reset_index(inplace=True)
            df.rename(columns={'Date':'date','Open':'open','High':'high','Low':'low','Last':'close','Volume':'volume'}, inplace=True)
            df.set_index('date', inplace=True)
            return resample_data(df, period).iloc[-days:]

        # # IEX: index=['date']
        # # columns=['open', 'high', 'low', 'close', 'volume']
        # df = source.DataReader(ticker, 'iex', start=START_DATE, end=END_DATE)
        # # df = feed.iex.daily.IEXDailyReader(symbols=ticker, start=START_DATE, end=END_DATE)
        # df.to_csv('/home/julia/trading_analysis/web/documents/{0}_iex.csv'.format(ticker))

        # # Tiingo: index=['symbol', 'date'], 200418:小天鹅, 000651:格力
        # # columns=['adjClose', 'adjHigh', 'adjLow', 'adjOpen', 'adjVolume', 'close', 'divCash', 'high', 'low', 'open', 'splitFactor', 'volume'],
        # df = source.get_data_tiingo(symbols=ticker, start=_START_DATE, end=_END_DATE, api_key=TIINGO_API_KEY)
        # df.reset_index(level='symbol', drop=True, inplace=True)
        # df.sort_index(ascending=True, inplace=True)
        # df.to_csv('/home/julia/trading_analysis/web/documents/{0}_tiingo.csv'.format(ticker))
        config = {}
        config['session'] = True
        config['api_key'] = TIINGO_API_KEY
        client = TiingoClient(config)
        df = client.get_dataframe(ticker, frequency='daily', startDate=_END_DATE-timedelta(days=days), endDate=_END_DATE)
        # df.to_csv('/Users/jingnie/startup/eshujupai/documents/{0}_tiingo.csv'.format(ticker))
        # df.to_csv('/home/julia/trading_analysis/web/documents/{0}_tiingo.csv'.format(ticker))
        # resample_data(df, period).to_csv(os.path.join(BASE_DIR, f'documents/{ticker}_tiingo.csv'))

        return resample_data(df, period)
    except:
        log.warn(traceback.print_exc())
        return None

def get_historical_data(ticker, file):
    df = None  # DataFrame()
    if file:
        # df = pd.read_csv(file, encoding='utf-8')
        df = read_data_from_file(file, ticker)
    elif ticker:
        df = read_data_from_feed(ticker)

    if df is None or df.empty:
        log.error('Cannot get the historical data for {0} or {1}'.format(file, ticker))
    return df

def get_indicators(df):
    suffix = '_signal'
    indicator_columns = [c for c in df.columns if c.endswith(suffix)]
    indicators = [c[:-len(suffix)] for c in indicator_columns]
    # print(indicator_columns)
    # df.to_csv('/home/julia/trading_analysis/web/documents/gold_run.csv')
    return indicators, indicator_columns

# Threaded function for queue processing.
class BacktestWorker(Thread):
    def __init__(self, threadID, args_queue, outputs):
        Thread.__init__(self)
        self.threadID = threadID
        self.args_queue = args_queue
        self.outputs = outputs

    def run(self):
        # print(f'Starting BacktestWorker {self.threadID}')
        while True:
            # Get the work from the queue and expand the tuple
            i, args = self.args_queue.get()
            try:
                self.outputs[i] = backtest(*args)
            finally:
                self.args_queue.task_done()

# Run backtest synchronous with single thread
def run(df, commission, ticker='', backtest_set=BACKTEST_SET):
    log.info(f'Run backtest {ticker}')
    # Enrich the average daily up and down information
    preprocess(df)

    # Calculate the technical indicators
    cal_technical_indicators(df)

    # Calculate machine learning indicators
    cal_ml_indicators(df)

    # Backtest with all signals and save the daily pnl in a DataFrame.
    indicators, indicator_columns = get_indicators(df)

    start = datetime.utcnow()
    can_short = check_short(ticker)
    # try:
    #     # Multi-processing
    #     args = ((df, commission, '{0}_signal'.format(i), i, can_short) for i in indicators)
    #     cpus = cpu_count()
    #     with Pool(processes=cpus) as pool:
    #         outputs = pool.starmap(backtest, args)
    # except:
    #     print(traceback.print_exc())
    #     # Multi-threading
    #     args_queue = Queue(maxsize=0)
    #     queue_length = len(indicators)
    #     num_threads = min(_MAX_BACKTEST_THREADS, queue_length)
    #     # load up the queue with the indicators and the index for each job (as a tuple):
    #     for i in range(queue_length):
    #         args = ((df, commission, indicator_columns[i], indicators[i], can_short))
    #         args_queue.put((i, args))
    #     outputs = [None] * len(indicators)
    #     for i in range(num_threads):
    #         worker = BacktestWorker(i, args_queue, outputs)
    #         worker.setDaemon(True)  # setting threads as "daemon" allows main program to exit eventually even if these dont finish correctly.
    #         worker.start()
    #     # now we wait until the queue has been processed
    #     args_queue.join()

    # Single thread
    outputs = []
    # Use BACKTEST_SET+1 row for backtest because the 1st is needed for the position of next day
    df_backtest = df[-backtest_set - 1:]
    for i in range(len(indicators)):
        output = backtest(df_backtest, commission, indicator_columns[i], indicators[i], can_short, backtest_set)
        outputs.append(output)

    log.info(f'{ticker}: backtest duration={datetime.utcnow()-start}')

    # Sort the daily pnl for all strategies. Sort the result by 'pnl_avg' descending.
    result = pd.concat(outputs, ignore_index=True)

    # Select the max return from each strategy
    result_summary = result.loc[result.groupby(['strategy'])['return_rate'].idxmax()]
    result_summary.sort_values(by=['return_rate', 'total_return'], ascending=[False, False], inplace=True)
    result_summary.dropna(inplace=True)
    result_detail = get_return(df_backtest, result_summary, can_short, backtest_set)

    # path = os.path.join(BASE_DIR,  f"documents/result/{ticker}_{datetime.utcnow().isoformat(timespec='minutes')}.csv")
    # result_summary.to_csv(path)

    if ticker.lower() in ('gold', 'us30', 'us10', 'us5'):
        print(f'addd-run::run:{ticker}: {result_summary.head(1).to_dict()}')

    return result_summary, result_detail


def check_short(ticker):
    '''
    :param ticker: string, stock ticker
    :return: bool, whether the stock can be short or not
    '''
    # Chinese stocks cannot be short. The Chinese ticker format is 000000
    if ticker.isdigit():
        log.info(f'{ticker} cannot be short')
        return False
    return True


def main():
    for ticker in ('arwr', 'gold', 'us30'):
        print(f'Run {ticker}')
        # file_path = f'/Users/jingnie/startup/eshujupai/documents/{ticker}.csv'
        # format_file_to_csv(file_path, ticker)
        # result_summary = pd.DataFrame()
        # for backtest_set in (5, 10, 20, 30, 40, 50, 70, 100):
        #     delete_backtest(tickers=[ticker])
        #     backtest_summary, _, _, _ = get_backtest(
        #         ticker, commission=0.0, period='D',
        #         file=file_path,
        #     )
        #     result_summary = backtest_summary
        #     result_summary['backtest_set'] = backtest_set
        # path = os.path.join(BASE_DIR,  f"documents/result/{ticker}_{datetime.utcnow().isoformat(timespec='minutes')}.csv")
        # result_summary.to_csv(path)

if __name__ == '__main__':
    main()