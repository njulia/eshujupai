from datetime import datetime
import pandas as pd
from predictapp.models import (
    Upload,
    Exchange,
    Index,
    Security,
    BacktestCondition,
    BacktestSummary,
    BacktestDetail
)
from predict.run import run
from predict.dataloader.data_loader import load_historical_data
from predict.settings import BACKTEST_SET
from web.settings import BASE_DIR
from utils.settings_index import indexes
import os
import csv
# import pytz
import json
import logging
import traceback


log = logging.getLogger(__name__)

def import_exchanges():
    # 'BATS', 'NASDAQ', 'OTCMKTS', 'NMFQS', 'OTCBB', 'PINK', 'SHE', 'SHG', 'NYSE ARCA', 'AMEX', 'NYSE MKT', 'NYSE',
    Exchange.objects.bulk_create([
        Exchange(code='BATS', name='BATS Global Markets', country='United states', timezone='US/Eastern'),
        Exchange(code='NMFQS', name='NMFQS', country='United states', timezone='US/Eastern'),
        Exchange(code='OTCBB', name='OTCBB', country='United states', timezone='US/Eastern'),
        Exchange(code='OTCMKTS', name='OTCMKTS', country='United states', timezone='US/Eastern'),
        Exchange(code='PINK', name='Pink Sheets', country='United states', timezone='US/Eastern'),
        Exchange(code='AMEX', name='NYSE Market (Amex)', country='United states', timezone='US/Eastern'),
        Exchange(code='NYSE', name='NYSE', country='United states', timezone='US/Eastern'),
        Exchange(code='NYSE_ARCA', name='NYSE ARCA', country='United states', timezone='US/Eastern'),
        Exchange(code='NYSE_MKT', name='NYSE MKT', country='United states', timezone='US/Eastern'),
        Exchange(code='NASDAQ', name='NASDAQ', country='United states', timezone='US/Eastern'),
        Exchange(code='SHG', name='Shanghai Stock Exchange', country='China', timezone='Asia/Hong_Kong'),
        Exchange(code='SHE', name='Shenzhen Stock Exchange', country='China', timezone='Asia/Hong_Kong'),
    ])

def import_securities():
    '''
    Import security from https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip
    AMEX: 39
    BATS: 238
    NASDAQ: 4734
    NMFQS: 31965
    OTCBB: 1772
    OTCMKTS: 4605
    PINK: 10169
    NYSE: 4342
    NYSE ARCA: 2078
    NYSE MKT: 166
    SHE: 2164 stocks
    SHG: 1488 stocks
    :return:
    '''

    try:
        path = os.path.join(BASE_DIR, 'documents/us-china.csv')
        print('supported_ticker: ', path)
        with open(path, newline='') as csv_file:
        # with open(path, encoding="utf8", errors='ignore') as csv_file:
            reader = csv.DictReader(csv_file, delimiter=',')
            for row in reader:
                security, created = Security.objects.update_or_create(ticker=row['ticker'],
                                    defaults={'exchange':row['exchange'], 'asset_type':row['asset_type'], 'currency':row['currency'],
                                              'volume':row['volume'] if 'volume' in row else 0.0, 'name': row['name'] if 'name' in row else ''})
                if created:
                    print('created ', row['ticker'])
                else:
                    print('updated ', row['ticker'])
    except:
        log.error(traceback.print_exc())

    count = Security.objects.count()
    log.info(f'import_securities: Imported {count} securities')
    print(f'Imported {count} securities')

def import_indexes():
    '''
    Import index from utils/settings_index.py to database
    :return:
    '''
    for i, (key, value) in enumerate(indexes.items()):
        tickers = json.dumps(value.index_tickers)
        print(f'import_indexes: {key}: {tickers}')
        index, created = Index.objects.update_or_create(symbol=key,
                         defaults = {'name':value.index_name, 'tickers':tickers})
        if created:
            log.info(f'import_indexes: Created Index: {key}')
    log.info(f'import_indexes: Import {Index.objects.count()} indexes')
    print(f'Import {Index.objects.count()} indexes')

def get_backtest(ticker, commission=0.0, file=None, period='D', backtest_set=BACKTEST_SET):
    '''
    :param ticker: string
    :param commission: float, commission per share
    :param file: string, file path of the historical data
    :return: BacktestSummary and BacktestDetail. start_time and end_time of the backtest range
    '''
    try:
        print('Backtest {0} with commission={1} for {2} {3} {4}'.format(ticker, commission, backtest_set, period, 'from '+file if file else ''))
        log.info('Backtest {0} with commission={1} for {2} {3} {4}'.format(ticker, commission, backtest_set, period, 'from '+file if file else ''))
        if file:
            df = load_historical_data(file, ticker)
            start_time = df.index[0]
            end_time = df.index[-1]
            backtest_summary, backtest_detail, _, _ = query_models(ticker=ticker, start_time=start_time, end_time=end_time)
        else:
            # backtest_summary, backtest_detail, start_time, end_time = query_models(ticker=ticker, end_time__gte=datetime.now(tz=pytz.UTC).date())
            backtest_summary, backtest_detail, start_time, end_time = query_models(ticker=ticker)
            if backtest_summary.empty or backtest_detail.empty:
                df = load_historical_data(ticker=ticker, period=period)

        if (backtest_summary.empty or backtest_detail.empty) and not df.empty:
            # Run backtest and predict
            start_time = df.index[0]
            end_time = df.index[-1]
            open_price = df['open'].iloc[-backtest_set]
            close_price = df['close'].iloc[-1]
            backtest_summary, backtest_detail = run(df, commission, ticker, backtest_set=backtest_set)
            if not backtest_summary.empty and not backtest_detail.empty:
                save_models(ticker, commission, start_time, end_time, open_price, close_price, backtest_summary, backtest_detail)

        return backtest_summary, backtest_detail, start_time, end_time
    except:
        log.error(traceback.print_exc())
        return None, None, None, None

def delete_backtest(tickers=[], exchanges=None, asset_type=None, currency=None, start_time=None, end_time=None):
    '''
    Bulk delete backtest related models: BacktestCondition, BacktestSummary and BacktestDetail
    If tickers, exchange, asset_type and currency are all None, delete backtest models for any Security
    Otherwise delete backtest models for Securities matching the filter conditions
    :param tickers: string. a list of tickers
    :param exchanges: string. a list of exchanges
    :param asset_type: string. asset type
    :param currency: string. currency code
    :param start_time: Start time of backtest range. If None, delete all
    :param end_time: End time of backtest range. If None, set to T-2
    :return:
    '''
    log.info(f'delete_backtest: tickers={tickers}, exchanges={exchanges}, asset_type={asset_type}, currency={currency}, start_time={start_time}, end_time={end_time}')
    print(f'delete backtest: tickers={tickers}, exchanges={exchanges}, asset_type={asset_type}, currency={currency}, start_time={start_time}, end_time={end_time}')
    print('delete_backtest: BacktestCondition models before delete: ', BacktestCondition.objects.count())
    print('delete_backtest: BacktestSummary models before delete: ', BacktestSummary.objects.count())
    print('delete_backtest: BacktestDetail models before delete: ', BacktestDetail.objects.count())

    BacktestCondition.objects.select_related('Security')
    kwargs = {}
    if tickers:
        kwargs['security__ticker__in'] = tickers
    if exchanges:
        kwargs['security__exchange__in'] = exchanges
    if asset_type:
        kwargs['security__asset_type__iexact'] = asset_type
    if currency:
        kwargs['security__currency__iexact'] = currency
    # if end_time is None:
    #     end_time = datetime.now(tz=pytz.UTC) - timedelta(days=2)
    # kwargs['end_time__lt'] = end_time
    if end_time:
        kwargs['end_time_lt'] = end_time
    if start_time:
        kwargs['start_time__gt'] = start_time

    # BacktestSummary, BacktestDetail are deleted when deleting BacktestCondition because "on_delete=models.CASCADE"
    # NO need to delete BacktestSummary, BacktestDetail seperately
    # Delete Model BacktestCondition
    backtest_conditions = BacktestCondition.objects.filter(**kwargs)
    log.info(f'delete_backtest: filter={kwargs}, count={backtest_conditions.count()}')
    backtest_conditions.delete()

    print('delete_backtest: BacktestCondition models after delete: ', BacktestCondition.objects.count())
    print('delete_backtest: BacktestSummary models after delete: ', BacktestSummary.objects.count())
    print('delete_backtest: BacktestDetail models after delete: ', BacktestDetail.objects.count())

def delete_models():
    '''
    Delete all models except User related models. Upload, Security, BacktestCondition, BacktestSummary, BacktestDetail
    :return:
    '''
    # Delete Model Upload
    log.info('delete_models: Upload models before delete: ', Upload.objects.all())
    Upload.objects.all().delete()
    log.info('delete_models: Upload models after delete: ', Upload.objects.all())
    print('Upload models after delete: ', Upload.objects.all())

    # BacktestCondition, BacktestSummary, BacktestDetail are deleted when deleting Security because "on_delete=models.CASCADE"
    # Delete Model Security
    log.info('delete_models: Security models before delete: ', Security.objects.all())
    Security.objects.all().delete()
    log.info('delete_models: Security models after delete: ', Security.objects.all())
    print('Security models after delete: ', Security.objects.all())

    # Delete Model BacktestCondition
    log.info('delete_models: BacktestCondition models before delete: ', BacktestCondition.objects.all())
    BacktestCondition.objects.all().delete()
    log.info('delete_models: BacktestCondition models after delete: ', BacktestCondition.objects.all())
    print('BacktestCondition models after delete: ', BacktestCondition.objects.all())

    # Delete Model BacktestSummary
    log.info('delete_models: BacktestSummary models before delete: ', BacktestSummary.objects.all())
    BacktestSummary.objects.all().delete()
    log.info('delete_models: BacktestSummary models after delete: ', BacktestSummary.objects.all())
    print('BacktestSummary models after delete: ', BacktestSummary.objects.all())

    # Delete Model BacktestDetail
    log.info('delete_models: BacktestDetail models before delete: ', BacktestDetail.objects.all())
    BacktestDetail.objects.all().delete()
    log.info('delete_models: BacktestDetail models after delete: ', BacktestDetail.objects.all())
    print('BacktestDetail models after delete: ', BacktestDetail.objects.all())

def query_models(ticker, **kwargs):
    # todo: add tzinfo to start_time and end_time
    '''
    :param ticker: string.
    :param kwargs: datetime. start_time and end_time in the BacktestCondition
    :return: DataFrame BacktestSummary.summary, DataFrame BacktestDetail.detail, Datatime BacktestCondition.start_time, Datatime BacktestCondition.end_time,
    '''
    try:
        log.info(f'query_models: ticker={ticker}, {kwargs}')

        security = Security.objects.get(ticker=ticker)
        # Get the backtest with the latest end_time because the filter returns QuerySet order by ['security', '-end_time', 'start_time']
        backtest_condition = BacktestCondition.objects.filter(security=security, **kwargs)[0]

        backtest_summary = BacktestSummary.objects.get(backtest_condition=backtest_condition)

        backtest_detail = BacktestDetail.objects.get(backtest_condition=backtest_condition)

        backtest_summary_df = pd.DataFrame.from_dict(backtest_summary.summary, orient='columns')
        backtest_summary_df.sort_values(by=['return_rate'], ascending=[False], inplace=True)

        # detail_df is in dictionary format if to_json(orient='columns') when saving the models
        backtest_detail_df = pd.DataFrame.from_dict(backtest_detail.detail, orient='columns')
        backtest_detail_df.index = pd.DatetimeIndex(backtest_detail_df.index)

        return backtest_summary_df, backtest_detail_df, backtest_condition.start_time, backtest_condition.end_time
    except:
        log.error(traceback.print_exc())
        log.error(f'query_models: Failed to get backtest results for {ticker}')
    return pd.DataFrame(), pd.DataFrame(), None, None

def save_models(ticker, commission, start_time, end_time, open_price, close_price, result_summary, result_detail):
    # Get or Create Security
    security, created = Security.objects.get_or_create(ticker=ticker)
    if created:
        log.info(f'save_models: Created Security: {security}')

    # Update or Create BacktestCondition with the best return_rate backtest result
    best_strategy = result_summary.nlargest(1, columns=['return_rate'], keep='first').iloc[0]
    backtest_condition, created = BacktestCondition.objects.update_or_create(security=security, start_time=start_time, end_time=end_time,
                                                                             open_price=open_price, close_price=close_price,
                                  defaults = {'strategy':best_strategy['strategy'], 'commission':best_strategy['commission'],
                                              'profit_factor':best_strategy['profit_factor'], 'loss_factor':best_strategy['loss_factor'],
                                              'total_return':best_strategy['total_return'], 'return_rate':best_strategy['return_rate'],
                                              'sharpe':best_strategy['sharpe'], 'drawdown':best_strategy['drawdown'], 'volatility': best_strategy['volatility']})
    if created:
        log.info(f'save_models: Created BacktestCondition: {backtest_condition}')


    # Get or Create BacktestSummary
    try:
        backtest_summary = BacktestSummary.objects.get(backtest_condition=backtest_condition)
    except:
        backtest_summary = BacktestSummary.objects.create(backtest_condition=backtest_condition,
                                                          summary=result_summary.to_json(orient='columns', date_format='iso'))
        log.info(f'save_models: Created BacktestSummary: {backtest_condition}')

    # Get or Create BacktestDetail
    try:
        backtest_detail = BacktestDetail.objects.get(backtest_condition=backtest_condition)
    except:
        backtest_detail = BacktestDetail.objects.create(backtest_condition=backtest_condition,
                                                        detail=result_detail.to_json(orient='columns', date_format='iso'))
        log.info(f'save_models: Created BacktestDetail: {backtest_condition}')
