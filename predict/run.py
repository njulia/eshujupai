import pandas as pd
pd.core.common.is_list_like = pd.api.types.is_list_like
from datetime import date, datetime
from predict.dataloader.data_loader import check_short
from predict.process import preprocess, backtest, get_return
from predict.technical_indicators import cal_technical_indicators
# from predict.ml.ml_indicator import cal_ml_indicators
from predict.settings import BACKTEST_DAYS
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
def run(df, commission=0, ticker='', backtest_days=BACKTEST_DAYS):
    log.info(f'Run backtest {ticker}')
    # Enrich the average daily up and down information
    preprocess(df)

    # Calculate the technical indicators
    cal_technical_indicators(df)

    # # Calculate machine learning indicators
    # cal_ml_indicators(df)

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
    # Use BACKTEST_DAYS+1 row for backtest because the 1st is needed for the position of next day
    df_backtest = df[-backtest_days - 1:]
    for i in range(len(indicators)):
        output = backtest(df_backtest, commission, indicator_columns[i], indicators[i], can_short, backtest_days)
        outputs.append(output)

    log.info(f'{ticker}: backtest duration={datetime.utcnow()-start}')

    # Sort the daily pnl for all strategies. Sort the result by 'pnl_avg' descending.
    result = pd.concat(outputs, ignore_index=True)

    # Select the max return from each strategy
    result_summary = result.loc[result.groupby(['strategy'])['return_rate'].idxmax()]
    result_summary.sort_values(by=['return_rate', 'total_return'], ascending=[False, False], inplace=True)
    result_summary.dropna(inplace=True)
    result_detail = get_return(df_backtest, result_summary, can_short, backtest_days)

    # path = os.path.join(BASE_DIR,  f"documents/result/{ticker}_{datetime.utcnow().isoformat(timespec='minutes')}.csv")
    # result_summary.to_csv(path)

    if ticker.lower() in ('gold', 'us30', 'us10', 'us5'):
        print(f'addd-run::run:{ticker}: {result_summary.head(1).to_dict()}')

    return result_summary, result_detail


def main():
    for ticker in ('arwr', 'gold', 'us30'):
        print(f'Run {ticker}')
        # file_path = f'/Users/jingnie/startup/eshujupai/documents/{ticker}.csv'
        # format_file_to_csv(file_path, ticker)
        # result_summary = pd.DataFrame()
        # for backtest_days in (5, 10, 20, 30, 40, 50, 70, 100):
        #     delete_backtest(tickers=[ticker])
        #     backtest_summary, _, _, _ = get_backtest(
        #         ticker, commission=0.0, period='D',
        #         file=file_path,
        #     )
        #     result_summary = backtest_summary
        #     result_summary['backtest_days'] = backtest_days
        # path = os.path.join(BASE_DIR,  f"documents/result/{ticker}_{datetime.utcnow().isoformat(timespec='minutes')}.csv")
        # result_summary.to_csv(path)

if __name__ == '__main__':
    main()