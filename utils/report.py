from predictapp.models import (
    BacktestCondition,
)
from predictapp.models_operation import query_models
from predictapp.views import format_backtest_summary
from predict.settings import PRICE_COLUMNS, SHOW_COLUMNS_CN
from utils.settings_index import BACKTEST_REPORT_STRATEGY_RANK
from graphos.sources.simple import SimpleDataSource
from graphos.renderers.gchart import LineChart, CandlestickChart
import numpy as np
from web.settings import BASE_DIR, DEBUG
import os
import matplotlib.pyplot as plt
from mpl_finance import candlestick2_ohlc
import six
from django.db.models.query import QuerySet
from datetime import datetime


SMALL_SIZE = 10
MEDIUM_SIZE = 12
BIG_SIZE = 14


def get_top_securities(n=10, exchanges=None, securities=None, lang='zh'):
    '''
    Get top n securities with best return_rate
    :param n: int. Number of items to retrieve
    :return: list. The securities retrieved
    '''
    kwargs = {}
    if securities:
        kwargs['security__ticker__in'] = securities
    if exchanges:
        kwargs['security__exchange__in'] = exchanges
    print(f'get_top_securities: n={n}, filter={kwargs}')
    backtests = BacktestCondition.objects.filter(**kwargs).order_by('-return_rate', 'security', 'end_time')[:n]
    topn = backtests.values_list('security__ticker', 'security__name', 'open_price', 'close_price', 'total_return', 'return_rate')
    tickers = [s[0] for s in topn]
    print(f'get_top_securities: get top {len(tickers)} securities: {tickers}')
    # Print table to a picture
    columns=["Ticker", "Company", "Open", "Close", "Total Return", "Return Rate(%)"] if lang=='en' else ["股票代码", "公司", "开盘价", "收盘价", "总收益", "收益率(%)"]
    table_image = '{0}_top.png'.format(datetime.now())
    render_mpl_table(topn, columns, table_image)
    return topn, tickers, table_image

def get_interactive_chart(request, tickers):
    '''
    Get the table and chart results of backtest for tickers
    :param request: httprequest
    :param tickers: list. The tickers of securities to retrieve
    :return: dictionary. The 'start_time', 'end_time', 'backtest_summary', 'return_chart' and 'price_chart' of each security.
    '''
    results = {}
    for ticker in tickers:
        saved_backtest_summary, saved_backtest_detail, start_time, end_time = query_models(ticker=ticker)  # , start_time=start_time, end_time=end_time)
        saved_backtest_summary_subset = saved_backtest_summary.iloc[:BACKTEST_REPORT_STRATEGY_RANK]
        backtest_summary_show = format_backtest_summary(request, saved_backtest_summary_subset)
        strategies = saved_backtest_summary_subset['strategy'].tolist()
        saved_backtest_detail.index = saved_backtest_detail.index.strftime('%Y-%m-%d')
        saved_backtest_detail.reset_index(inplace=True)

        # Plot return of each strategy in LineChart
        column_list = ['index'] + strategies
        return_data = saved_backtest_detail[column_list].values.tolist()
        return_data.insert(0, column_list)
        data_source = SimpleDataSource(data=return_data)
        return_chart = LineChart(data_source,
                                 width="100%",
                                 options={'title': 'Return',
                                          'chartArea': {'left': "10%", 'top': "10%", 'width': "70%", 'height': "60%"},
                                          'legend': {'position': 'right', 'maxLines': 5,
                                                     'textStyle': {'color': 'blue', 'fontSize': MEDIUM_SIZE}},
                                          'height': 'window.innerHeight',
                                          })
        # Plot prices ('low', 'open', 'close', 'high') in CandlestickChart
        column_list = ['index'] + PRICE_COLUMNS
        price_data = saved_backtest_detail[column_list].values.tolist()
        price_data.insert(0, column_list)
        data_source = SimpleDataSource(data=price_data)
        if request.LANGUAGE_CODE == 'zh-cn':
            # Red for rising, Green for falling in China
            risingclolor = 'red'
            fallingcolor = 'green'
        else:
            risingclolor = 'green'
            fallingcolor = 'red'
        price_chart = CandlestickChart(data_source,
                                       width="100%",
                                       options={'title': 'Price',
                                                'legend': 'none',
                                                'chartArea': {'left': "10%", 'top': "10%", 'width': "70%",
                                                              'height': "60%"},
                                                'candlestick': {
                                                    'risingColor': {'fill': risingclolor, 'stroke': 'black',
                                                                    'strokeWidth': 0.5},
                                                    'fallingColor': {'fill': fallingcolor, 'stroke': 'black',
                                                                     'strokeWidth': 0.5}
                                                },
                                                'colors': ['red', 'brown', 'magenta'],
                                                'height': 'window.innerHeight',
                                                }
                                       )
        results[ticker] = {
            'start_time': start_time,
            'end_time': end_time,
            'backtest_summary': backtest_summary_show.to_html(index=False, na_rep=''),
            'return_chart': return_chart,
            'price_chart': price_chart,
            }
    return results

def get_static_chart(request, tickers):
    '''
      Get the table and chart results of backtest for tickers
      :param request: httprequest
      :param tickers: list. The tickers of securities to retrieve
      :return: dictionary. The 'start_time', 'end_time', 'backtest_summary', 'return_chart' and 'price_chart' of each security.
      '''
    results = {}
    for ticker in tickers:
        saved_backtest_summary, saved_backtest_detail, start_time, end_time = query_models(ticker=ticker)  # , start_time=start_time, end_time=end_time)
        saved_backtest_summary_subset = saved_backtest_summary.iloc[:BACKTEST_REPORT_STRATEGY_RANK]
        backtest_summary_show = format_backtest_summary(request, saved_backtest_summary_subset)
        # Print table to a picture
        table_image = f'{ticker}_table.png'
        render_mpl_table(backtest_summary_show.values, SHOW_COLUMNS_CN, table_image)
        strategies = saved_backtest_summary_subset['strategy'].tolist()
        saved_backtest_detail.index = saved_backtest_detail.index.strftime('%Y-%m-%d')
        # saved_backtest_detail.reset_index(inplace=True)

        # ax1 = plt.subplot2grid((2, 1), (0, 0), colspan=1, rowspan=1)
        # ax2 = plt.subplot2grid((2, 1), (1, 0))
        fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(8,5))
        plt.rc('font', size=MEDIUM_SIZE)
        plt.rc('xtick', labelsize=MEDIUM_SIZE)
        plt.rc('ytick', labelsize=MEDIUM_SIZE)
        plt.rc('legend', fontsize=MEDIUM_SIZE)

        # Plot return of each strategy in LineChart
        saved_backtest_detail[strategies].plot(ax=ax1)
        ax1.set_xticks(np.arange(len(saved_backtest_detail)))
        ax1.set_xticklabels(saved_backtest_detail.index, rotation=-90)
        ax1.set_ylabel('收益', fontsize=BIG_SIZE)
        # ax1.legend(loc='upper left', fontsize=16)

        # Plot prices ('low', 'open', 'close', 'high') in CandlestickChart
        if request.LANGUAGE_CODE == 'zh-cn':
            # Red for rising, Green for falling in China
            risingclolor = 'red'
            fallingcolor = 'green'
        else:
            risingclolor = 'green'
            fallingcolor = 'red'
        cl1 = candlestick2_ohlc(ax=ax2, opens=saved_backtest_detail['open'], highs=saved_backtest_detail['high'], lows=saved_backtest_detail['low'],
                               closes=saved_backtest_detail['close'], width=0.4, colorup=risingclolor, colordown=fallingcolor)
        ax2.set_xticks(np.arange(len(saved_backtest_detail)))
        ax2.set_xticklabels(saved_backtest_detail.index, rotation=-90)
        ax2.set_ylabel('价格', fontsize=BIG_SIZE)

        # save the result
        return_image = f'{ticker}_return.png'
        root = 'predictapp/static/images/' if DEBUG else 'static/images/'
        plt.savefig(os.path.join(BASE_DIR, root, return_image), dpi=80, bbox_inches='tight', pad_inches=0.1)

        results[ticker] = {
            'start_time': start_time,
            'end_time': end_time,
            'backtest_summary': backtest_summary_show.to_html(index=False, na_rep=''),
            'return_chart': return_image,
            'tables': (table_image,),
        }
    return results

def render_mpl_table(data, columns, file_name, col_width=1.6, row_height=0.3, font_size=BIG_SIZE,
                     header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
                     bbox=[0, 0, 1, 1], header_columns=0,
                     ax=None, **kwargs):
    '''
    Save QuerySet or np array to a picture of table
    :param data:
    :param columns:
    :param file_name:
    :param col_width:
    :param row_height:
    :param font_size:
    :param header_color:
    :param row_colors:
    :param edge_color:
    :param bbox:
    :param header_columns:
    :param ax:
    :param kwargs:
    :return:
    '''
    if ax is None:
        if isinstance(data, QuerySet):
            shape = (data.count(), len(columns))
        else:
            shape = data.shape
        size = (np.array(shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        fig, ax = plt.subplots(figsize=size)
        ax.axis('off')

    mpl_table = ax.table(cellText=data, bbox=bbox, colLabels=columns, **kwargs)

    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    for k, cell in six.iteritems(mpl_table._cells):
        cell.set_edgecolor(edge_color)
        if k[0] == 0 or k[1] < header_columns:
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor(header_color)
        else:
            cell.set_facecolor(row_colors[k[0]%len(row_colors)])

    # save the result

    root = 'predictapp/static/images/' if DEBUG else 'static/images/'
    path = os.path.join(BASE_DIR, root, file_name)
    plt.savefig(path, dpi=80, bbox_inches='tight', pad_inches=0)
    # return path, ax
