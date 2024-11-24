from celery import current_task, Task
from celery.decorators import periodic_task, task
from celery.result import states
from predictapp.models import (
    Security,
)
from predict.bulk_backtest import run_bulk_backtest_multithread, run_bulk_backtest_singlethread
from predict.run import get_indicators, check_short
from predict.process import preprocess, backtest, get_return
from predict.technical_indicators import cal_technical_indicators
from predict.ml.ml_indicator import cal_ml_indicators
from predict.run import read_data_from_feed, read_data_from_file
from predict.settings import BACKTEST_SET
from predictapp.models_operation import save_models, query_models
from datetime import datetime
import pandas as pd
import pytz
import logging
import traceback


log = logging.getLogger(__name__)


class BackTestTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        log.warning('BackTestTask {0!r} failed: {1!r}'.format(task_id, exc))
        super(BackTestTask, self).on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, exc, task_id, args, kwargs):
        log.info('BackTestTask {0!r} success: {1!r}'.format(task_id, exc))
        super(BackTestTask, self).on_success(exc, task_id, args, kwargs)

@task(name='run_backtest_task')
def run_backtest_task(df, commission, ticker):
    log.info(f'run_backtest_task: Run backtest asynchronous {ticker}')

    # Enrich the average daily up and down information
    preprocess(df)
    # Calculate the technical indicators
    cal_technical_indicators(df)
    # Calculate machine learning indicators
    cal_ml_indicators(df)
    # Backtest with all signals and save the daily pnl in a DataFrame.
    indicators, indicator_columns = get_indicators(df)

    can_short = check_short(ticker)

    # Single thread
    start = datetime.utcnow()
    outputs = []
    n = len(indicators)
    for i in range(n):
        output = backtest(df, commission, indicator_columns[i], indicators[i], can_short)
        outputs.append(output)
        if (i % 10 == 0):
            process_percent = int(100 * float(i) / float(n))
            current_task.update_state(state='PROGRESS',
                                      meta={'process_percent': process_percent})
            log.info(f'progressing {process_percent}%')
    current_task.update_state(state='SUCCESS')
    log.inforint(f'{ticker}: Asynchronous backtest duration={datetime.utcnow() - start}')

    # Sort the daily pnl for all strategies. Sort the result by 'pnl_avg' descending.
    result = pd.concat(outputs, ignore_index=True)
    # Select the max return from each strategy
    result_summary = result.loc[result.groupby(['strategy'])['return_rate'].idxmax()]
    result_summary.sort_values(by=['return_rate'], ascending=[False], inplace=True)
    result_summary.dropna(inplace=True)
    # Get the backtest result of each day for each strategy
    result_detail = get_return(df, result_summary, can_short)

    return result_summary, result_detail

@task(name='run_bulk_backtest_multithread_task')
def run_bulk_backtest_multithread_task(exchanges=[], delete=False, tickers=None):
    log.info('Run bulk backtest multi-threading asynchronous')
    kwargs = {}
    if exchanges:
        kwargs['exchange__in'] = exchanges
    if not tickers:
        tickers = Security.objects.filter(**kwargs).values_list('ticker', flat=True)
    run_bulk_backtest_multithread(tickers, delete)

@task(name='run_bulk_backtest_singlethread_task')
def run_bulk_backtest_singlethread_task(exchanges=[], delete=False, tickers=None):
    log.info('Run bulk backtest single-threading asynchronous')
    kwargs = {}
    if exchanges:
        kwargs['exchange__in'] = exchanges
    if not tickers:
        tickers = Security.objects.filter(**kwargs).values_list('ticker', flat=True)
    run_bulk_backtest_singlethread(tickers, delete)

# @periodic_task(run_every=(crontab(hour=16, minute=00, day_of_week='1-5')), name="backtest_eod_she")
# def backtest_eod_she():
#     run_bulk_backtest_singlethread(['SHE'])
#
# @periodic_task(run_every=(crontab(hour=12, minute=00, day_of_week='1-5')), name="backtest_eod_shg")
# def backtest_eod_shg():
#     run_bulk_backtest_singlethread(['SHG'])
#
# @periodic_task(run_every=(crontab(hour=6, minute=00, day_of_week='1-5')), name="backtest_eod_nasdaq")
# def backtest_eod_nasdaq():
#     run_bulk_backtest_singlethread(['NASDAQ'])
#
# @periodic_task(run_every=(crontab(hour=23, minute=50, day_of_week='1-5')), name="backtest_eod_nyse")
# def backtest_eod_nyse():
#     run_bulk_backtest_singlethread(['NYSE'])

@task(name='get_backtest_task', track_started=True, base=BackTestTask)
def get_backtest_task(ticker, commission=0.0, file=None, period='D'):
    '''
    :param ticker: string
    :param commission: float, commission per share
    :param file: string, file path of the historical data
    :return: BacktestSummary and BacktestDetail. start_time and end_time of the backtest range
    '''
    def _run_backtest(df, commission, ticker):
        log.info(f'get_backtest_task: Run backtest asynchronous: {ticker}')

        # Enrich the average daily up and down information
        preprocess(df)
        # Calculate the technical indicators
        cal_technical_indicators(df)
        # Calculate machine learning indicators
        cal_ml_indicators(df)
        # Backtest with all signals and save the daily pnl in a DataFrame.
        indicators, indicator_columns = get_indicators(df)

        can_short = check_short(ticker)

        # Single thread
        start = datetime.utcnow()
        outputs = []
        # Use BACKTEST_SET+1 row for backtest because the 1st is needed for the position of next day
        df_backtest = df[-BACKTEST_SET-1:]

        n = len(indicators)
        for i in range(n):
            output = backtest(df_backtest, commission, indicator_columns[i], indicators[i], can_short)
            outputs.append(output)
            if (i % 10 == 0):
                process_percent = int(100 * i / float(n))
                current_task.update_state(state='PROCESSING',
                                          meta={'process_percent': process_percent})
                log.info(f'get_backtest_task: update state: {process_percent}%')
        current_task.update_state(state=states.SUCCESS,
                                  meta={'process_percent': 100})

        log.info(f'get_backtest_task: {ticker}: Asynchronous backtest duration={datetime.utcnow() - start}')

        # Sort the return_rate for all strategies. Sort the result by 'return_rate' descending.
        result = pd.concat(outputs, ignore_index=True)
        # Select the max return from each strategy
        result_summary = result.loc[result.groupby(['strategy'])['return_rate'].idxmax()]
        result_summary.sort_values(by=['return_rate'], ascending=[False], inplace=True)
        result_summary.dropna(inplace=True)

        # Get the backtest result of each day for each strategy
        result_detail = get_return(df_backtest, result_summary, can_short)
        return result_summary, result_detail

    try:
        if file:
            df = read_data_from_file(file, ticker)
            start_time = df.index[0]
            end_time = df.index[-1]
            backtest_summary, backtest_detail, _, _ = query_models(ticker=ticker, start_time=start_time, end_time=end_time)
        else:
            # backtest_summary, backtest_detail, start_time, end_time = query_models(ticker=ticker, end_time__gte=datetime.now(tz=pytz.UTC).date())
            backtest_summary, backtest_detail, start_time, end_time = query_models(ticker=ticker)
            if backtest_summary.empty or backtest_detail.empty:
                df = read_data_from_feed(ticker, period=period)

        if (backtest_summary.empty or backtest_detail.empty) and not df.empty:
            # Run backtest and predict
            start_time = df.index[0]
            end_time = df.index[-1]
            open_price = df['open'].iloc[-BACKTEST_SET]
            close_price = df['close'].iloc[-1]
            backtest_summary, backtest_detail = _run_backtest(df, commission, ticker)
            if not backtest_summary.empty and not backtest_detail.empty:
                save_models(ticker, commission, start_time, end_time, open_price, close_price, backtest_summary, backtest_detail)
        return ticker, start_time, end_time
    except Exception as ex:
        log.warning(traceback.print_exc())
        log.warning(f'Failed to run get_backtest_task')
        current_task.update_state(
            state=states.FAILURE,
            meta={
                'exc_type': type(ex).__name__,
                'exc_message': traceback.format_exc().split('\n'),
                'custom': f'Failed to run backtest for {ticker}'
            })
    return ticker, None, None
