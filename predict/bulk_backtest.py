from predict.run import read_data_from_feed
from predictapp.models_operation import get_backtest, delete_backtest
from predictapp.models import (
    Security,
)
from predict.settings import MAX_THREADS
from numpy import array_split
from datetime import datetime
from threading import Thread
import logging


log = logging.getLogger(__name__)


class CalcVolume(Thread):
    def __init__(self, threadID, tickers):
        Thread.__init__(self)
        self.threadID = threadID
        self.tickers = tickers

    def run(self):
        # print(f'CalVolume: Starting thread {self.threadID}')
        for ticker in self.tickers:
            df = read_data_from_feed(ticker)
            if df is None or df.empty:
                log.error('CalcVolume: Failed to get the EOD data for {0}'.format(ticker))
                continue
            volume_mean = df['volume'].mean()
            security = Security.objects.get(ticker=ticker)
            security.volume = volume_mean
            security.save()

def run_calc_volume():
    tickers = Security.objects.all().values_list('ticker', flat=True)
    ticker_chunks = array_split(tickers, MAX_THREADS)

    threads = []
    for i in range(MAX_THREADS):
        thread = CalcVolume(i, ticker_chunks[i])
        thread.start()
        threads.append(thread)

    for t in threads:
        t.join()

class BulkBacktest(Thread):
    def __init__(self, threadID, tickers):
        Thread.__init__(self)
        self.threadID = threadID
        self.tickers = tickers

    def run(self):
        # Get lock to synchronize threads
        # threadLock.acquire()

        # Backtest for all tickers
        commission = 0.0
        for ticker in self.tickers:
            # If there is Backtest results of this ticker in the DB (no matter the backtest duration), don't run backtest
            get_backtest(ticker)

            # # Run backtest no matter there is Backtest results of this ticker in the DB
            # df = read_data_from_feed(ticker)
            # if df is None or df.empty:
            #     log.error('BulkBacktest: Failed to get the EOD data for {0}'.format(ticker))
            #     continue
            # start_time = df.index[0]
            # end_time = df.index[-1]
            # open_price = df['open'].iloc[-BACKTEST_SET]
            # close_price = df['close'].iloc[-1]
            # backtest_summary, backtest_detail = run(df, commission)
            # # backtest_summary, backtest_detail = run_backtest_task.delay(df, commission)
            # if not backtest_summary.empty and not backtest_detail.empty:
            #     save_models(ticker, commission, start_time, end_time, open_price, close_price, backtest_summary, backtest_detail)
            #     log.info(f'BulkBacktest: Save backtest {ticker}_{start_time}_{end_time}')

def run_bulk_backtest_multithread(tickers=[], delete=False):
    '''
    Run backtest for sepcified tickers at the end of day
    :param ticker: list of tickers. If it is [], check all exchanges and tickers of Model Security
    :param delete: whether delete the BacktestCondition, BacktestSummary and BacktestDetail or not
    :return:
    '''
    start = datetime.utcnow()

    if delete:
        # Delete all BacktestCondition, BacktestSummary and BacktestDetail for T-2
        delete_backtest(tickers=tickers)

    # Bulk backtest with multi-threading. Split all tickers into MAX_THREADS chunks
    ticker_chunks = array_split(tickers, MAX_THREADS)
    log.info(f'run_bulk_backtest_multithread: Run bulk backtest with {MAX_THREADS} threads: {ticker_chunks}')
    threads = []
    for i in range(MAX_THREADS):
        thread = BulkBacktest(i, ticker_chunks[i])
        thread.start()
        threads.append(thread)

    for t in threads:
        t.join()

    # Bulk backtest with single thread
    for ticker in tickers:
        get_backtest(ticker)

    end = datetime.utcnow()
    log.info(f'run_bulk_backtest_multithread: Tickers={len(tickers)}, Start={start}, End={end}, Duration={end-start}')

def run_bulk_backtest_singlethread(tickers=[], delete=False):
    '''
    Run backtest for sepcified tickers at the end of day
    :param tickers: list of tickers. If it is [], check all exchanges and tickers of Model Security
    :param delete: whether delete the BacktestCondition, BacktestSummary and BacktestDetail or not
    :return:
    '''
    start = datetime.utcnow()

    if delete:
        # Delete all BacktestCondition, BacktestSummary and BacktestDetail for T-2
        delete_backtest(tickers=tickers)

    log.info(f'run_bulk_backtest_singlethread: {tickers}')
    # Bulk backtest with single thread
    for ticker in tickers:
        print(f'run_bulk_backtest_singlethread: {ticker}')
        get_backtest(ticker)

    end = datetime.utcnow()
    log.info(f'run_bulk_backtest_singlethread: Tickers={len(tickers)}, Start={start}, End={end}, Duration={end-start}')

