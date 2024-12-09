import os
import csv
import json
import time
import random
import pytz
import logging
import traceback
from datetime import datetime
from django.template.loader import render_to_string
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from graphos.sources.simple import SimpleDataSource
from graphos.renderers.gchart import LineChart, CandlestickChart
from celery.result import AsyncResult
from predict.settings import SHOW_COLUMNS, PRICE_COLUMNS, PUBLIC_STRATEGY_RANK, PRIVATE_STRATEGY_RANK, BACKTEST_SET
from predictapp.models_operation import (
    query_models,
    get_userpayment,
    delete_backtest,
    import_indexes,
    get_backtest,
)
from predictapp.models import (
    Index,
    Security,
)
from predictapp.forms import (
    UploadForm,
)
from predictapp.tasks import get_backtest_result, get_backtest_task_asyn
# from gateway import ib


log = logging.getLogger(__name__)


def home(request):
    if request.user.is_authenticated:
        return redirect('trading')
    else:
        return redirect('instruction')

def get_saved_result(request):
    # Get saved backtest result
    ticker = request.session['ticker']
    # start_time = datetime.fromisoformat(request.session['start_time'])  # fromisoformat is new in python 3.7
    # end_time = datetime.fromisoformat(request.session['end_time'])      # fromisoformat is new in python 3.7
    start_time = datetime.strptime(request.session['start_time'], '%Y-%m-%dT%H:%M:%S')
    end_time = datetime.strptime(request.session['end_time'], '%Y-%m-%dT%H:%M:%S')

    saved_backtest_summary, saved_backtest_detail, _, _ = query_models(ticker=ticker, start_time=start_time, end_time=end_time)
    if saved_backtest_summary.empty or saved_backtest_detail.empty:
        saved_backtest_summary, saved_backtest_detail, _, _ = query_models(ticker=ticker)

    _, is_paid = get_userpayment(request.user)
    if is_paid:
        saved_backtest_summary_subset = saved_backtest_summary.iloc[:PRIVATE_STRATEGY_RANK]
        strategies = saved_backtest_summary_subset['strategy'].tolist()
    else:
        saved_backtest_summary_subset = saved_backtest_summary.iloc[-PUBLIC_STRATEGY_RANK:]
        strategies = saved_backtest_summary_subset['strategy'].tolist()
    detail_columns_chosen = PRICE_COLUMNS + strategies
    return saved_backtest_summary_subset, saved_backtest_detail[detail_columns_chosen], ticker, start_time, end_time, strategies, is_paid

def format_backtest_summary(request, df):
    '''
    Translate SHOW_COLUMN to other language
    :param request: HttpRequest
    :param df: Backtest summary dataframe
    :return: Dataframe for display
    '''
    if request.LANGUAGE_CODE == 'zh-cn':
        df['predict_signal']=df['predict_signal'].map({1: '买入', -1:'卖出'})
        columns_name = {'strategy':'策略', 'total_return':f'总收益({BACKTEST_SET}天)', 'return_rate':'收益率', 'sharpe':'夏普比率', 'drawdown':'最大回撤', 'volatility':'波动率',
                      'predict_signal':'预测信号', 'limit_price':'挂单价', 'predict_take_profit':'预测止盈位', 'predict_stop_loss':'预测止损位'}
    else:
        df['predict_signal']=df['predict_signal'].map({1: 'long', -1: 'short'})
        columns_name = {'strategy': 'Strategy', 'total_return': f'Total Return({BACKTEST_SET}days)', 'return_rate': 'Return Rate',
                        'sharpe': 'Sharpe', 'drawdown': 'Drawdown', 'volatility': 'Volatility',
                        'predict_signal': 'Predict Signal', 'limit_price': 'Limit Price', 'predict_take_profit': 'Take Profit',
                        'predict_stop_loss': 'Stop Loss'}
    return df[SHOW_COLUMNS].rename(columns=columns_name)

def export_security(request):
    '''
    Export Model security from database to csv file
    :param request:
    :return: csv file
    '''
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="supported_securities.csv"'
    writer = csv.writer(response)
    writer.writerow(['ticker', 'exchange', 'asset_type', 'currency'])
    securities = Security.objects.all().values_list('ticker', 'exchange', 'asset_type', 'currency')
    writer.writerows(securities)
    return response

def instruction(request):
    try:
        return render(request, 'instruction.html')
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html', {'error': _('Failed to show instruction')})

def contact(request):
    try:
        # delete_models()
        # import_exchanges()
        # import_securities()
        import_indexes()
        # delete_backtest(tickers=[ 'AAPL2'] )
        # delete_backtest(start_time=date(year=2018, month=2, day=15))
        # run_calc_volume()

        return render(request, 'contact.html')
    except:
        print(traceback.print_exc())
        return render(request, '404.html', {'error': _('Failed to show contact information')})

def terms_service(request):
    try:
        return render(request, 'terms_service.html')
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html', {'error': _('Failed to show terms of service')})

def privacy_policy(request):
    try:
        return render(request, 'privacy_policy.html')
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html', {'error': _('Failed to show privacy policy')})

def reports(request):
    try:
        reports = {}
        for f in os.listdir('static/reports'):
            try:
                if f.endswith('html') or f.endswith('pdf'):
                    key = f[f.find('_') + 1:-5]  # remove the date and '.html' in the file name
                    date = f[:f.find('_')]  # get the date in the file name
                    # name = '沪深A股' if key == 'None' else indexes[key].index_name
                    name = Index.objects.get(symbol=key).name
                    reports[f] = f'{date}_{name}'
            except:
                log.error(traceback.print_exc())
                continue

        context = {'reports': reports}
        log.error(f'context={context}')
        return render(request, 'predictapp/reports.html', context)
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html', {'error:': _('Failed to show research reports')})

def upload_historical_data(request):
    try:
        if 'job' in request.GET:
            job_id = request.GET['job']
            job = AsyncResult(job_id)
            try:
                state = job. state
                data = job.result
            except:
                state = 'Starting'
                data = ''
            context = {
                'state': state,
                'data': data,
                'task_id': job_id,
            }
            return render(request, "predictapp/show_t.html", context)

        if request.method == 'POST':
            form = UploadForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                ticker = form.cleaned_data['ticker']
                commission = form.cleaned_data['commission']
                uploaded_file = form.cleaned_data['document']
                uploaded_file_path = ''
                # uploaded_file = request.FILES.get('document')

                # If there is a backtest result in the database, show the result directly
                if not uploaded_file:
                    backtest_summary, backtest_detail, start_time, end_time = query_models(ticker=ticker, end_time__gte=datetime.now(tz=pytz.UTC).date())
                    if not backtest_summary.empty or not backtest_detail.empty:
                        request.session['ticker'] = ticker
                        request.session['start_time'] = start_time.strftime('%Y-%m-%dT%H:%M:%S')
                        request.session['end_time'] = end_time.strftime('%Y-%m-%dT%H:%M:%S')
                        backtest_summary_show = format_backtest_summary(request, backtest_summary)
                        user_payment, is_paid = get_userpayment(request.user)
                        if is_paid:
                            return render(request, 'predictapp/backtest_private.html',
                                          {'result': backtest_summary_show.iloc[:PRIVATE_STRATEGY_RANK].to_html(index=False, na_rep=''),
                                           'ticker': ticker, 'start_time': start_time, 'end_time': end_time})
                        return render(request, 'predictapp/backtest_public.html',
                                          {'result': backtest_summary_show.iloc[-PUBLIC_STRATEGY_RANK:].to_html(index=False, na_rep=''),
                                           'public_rank': PUBLIC_STRATEGY_RANK,
                                           'private_rank': PRIVATE_STRATEGY_RANK,
                                           'ticker': ticker, 'start_time': start_time, 'end_time': end_time})
                else:
                    uploaded_file_path = form.instance.document.path

                # Run backtest asynchronous
                job = get_backtest_task_asyn.delay(ticker, commission, uploaded_file_path)
                return HttpResponseRedirect(reverse('upload') + '?job=' + job.id)
                #res = get_backtest_result(ticker, uploaded_file_path, commission)
                #print(len(res))
        else:
            form = UploadForm()
        return render(request, 'predictapp/upload_historical_data.html',
                      {'form': form})
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html',
                      {'error': _('Failed to run the backtest. Please upload the file with historical data.')})

def backtest_table(request):
    try:
        backtest_summary, backtest_detail, ticker, start_time, end_time, _, is_paid = get_saved_result(request)
        backtest_summary_show = format_backtest_summary(request, backtest_summary)

        if is_paid:
            return render(request, 'predictapp/backtest_private.html',
                          {'result': backtest_summary_show.to_html(index=False, na_rep=''),
                           'ticker': ticker, 'start_time': start_time, 'end_time': end_time})
        return render(request, 'predictapp/backtest_public.html',
                      {'result': backtest_summary_show.to_html(index=False, na_rep=''),
                       'public_rank': PUBLIC_STRATEGY_RANK,
                       'private_rank': PRIVATE_STRATEGY_RANK,
                       'ticker': ticker, 'start_time': start_time, 'end_time': end_time})
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html',
                      {'error': _('Failed to load backtest table')})

def backtest_figure(request):
    try:
        backtest_summary, backtest_detail, _, _, _, strategies, _ = get_saved_result(request)
        backtest_detail.index = backtest_detail.index.strftime('%Y-%m-%d')
        backtest_detail.reset_index(inplace=True)

        # Plot return of each strategy in LineChart
        column_list = ['index'] + strategies
        return_data = backtest_detail[column_list].values.tolist()
        return_data.insert(0, column_list)
        data_source = SimpleDataSource(data=return_data)
        return_chart = LineChart(data_source,
                          width="100%",
                          # height="100%",
                          options={'title': 'Return',
                                   'chartArea': {'left': "10%", 'top': "10%", 'width': "70%", 'height': "60%"},
                                   'legend': {'position': 'right', 'maxLines':5, 'textStyle': {'color': 'blue', 'fontSize': 12}},
                                   'height': 'window.innerHeight',
                                   # 'width': 'window.innerWidth',
                                   # 'explorer': {
                                   #     'actions': ['dragToZoom', 'rightClickToReset'],
                                   #     'axis': 'horizontal',
                                   #     'keepInBounds': 'true'},
                                   })
        # Plot prices ('low', 'open', 'close', 'high') in CandlestickChart
        column_list = ['index'] + PRICE_COLUMNS
        price_data = backtest_detail[column_list].values.tolist()
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
                                       # height="100%",
                                       options={'title': 'Price',
                                                'legend': 'none',
                                                'chartArea': {'left': "10%", 'top': "10%", 'width': "70%", 'height': "60%"},
                                                'candlestick': {
                                                               'risingColor': {'fill': risingclolor, 'stroke': 'black', 'strokeWidth':0.5},
                                                               'fallingColor': {'fill': fallingcolor, 'stroke': 'black', 'strokeWidth':0.5}
                                                               },
                                                'colors': ['red','brown', 'magenta'],
                                                'height': 'window.innerHeight',
                                                # 'width': 'window.innerWidth',
                                                }
                                       )

        context = {'return_chart': return_chart,
                   'price_chart': price_chart
                   }
        return render(request, 'predictapp/backtest_figure.html', context)
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html',
                      {'error': _('Failed to load backtest figure')})

def poll_state(request):
    """ A view to report the progress to the user """
    return_value = {'state': 'Processing'}
    if request.is_ajax():
        if 'task_id' in request.POST.keys() and request.POST['task_id']:
            task_id = request.POST['task_id']
            task = AsyncResult(task_id)

            try:
                state = task.state or task.status
                return_value['state'] = state
                result = task.result
                return_value['data'] = result

                if state in ("SUCCESS",):
                    if not result[1] or not result[2]:
                        # If task result is (ticker, None, None), it means the backtest failed
                        return_value['state'] = 'FAILURE'
                    else:
                        request.session['ticker'] = result[0]
                        request.session['start_time'] = result[1][:-1]
                        request.session['end_time'] = result[2][:-1]
            except:
                # log.error(traceback.print_exc())
                return_value['data'] = 'Failed to get state or result'
        else:
            return_value['data'] = 'No task_id in the request'
    else:
        return_value['data'] = 'This is not an ajax request'

    json_data = json.dumps(return_value)
    print(f'return_value={return_value}, json_data={json_data}')
    return HttpResponse(json_data, content_type='application/json')


# def trading(request):
#     try:
#         if request.method == 'POST':
#             form = UploadForm(request.POST, request.FILES)
#             if form.is_valid():
#                 form.save()
#                 ticker = form.cleaned_data['ticker']
#                 commission = form.cleaned_data['commission']
#                 uploaded_file = form.cleaned_data['document']
#                 uploaded_file_path = form.instance.document.path if uploaded_file else ''
#
#                 # todo: delete this for block, it is for paper account
#                 app = ib.IBApp()
#                 with app.connect("127.0.0.1", 7497, clientId=0) as conn:
#                 # wait_connect = 100
#                 # while wait_connect > 0:
#                 #     if app.isConnected():
#                 #         break
#                 #     t=random.gauss()
#                 #     time.sleep(random.gauss())
#                 #     print(f'addd-sleep {t} secs')
#
#                     app.cancel_position(tickers='all') # cancel all positions before placing new orders
#                     for ticker in ['us30',]:
#                     #for ticker in ['ARWR', 'PDD', 'JD', 'ZM']:
#                             # ('gold', 'us30', 'us10', 'us5'):
#                         delete_backtest(tickers=[ticker])
#                         backtest_summary, backtest_detail, start_time, end_time = get_backtest(
#                             ticker, commission=0, period='D',
#                             #file=file_path,
#                         )
#                         best_strategy = backtest_summary.nlargest(1, ['return_rate'], keep='first').to_dict(orient='records')[0]
#                         print(f'addd-best strateggy of {ticker}: {best_strategy}')
#
#                         backtest_summary_show = format_backtest_summary(request, backtest_summary)
#                         request.session['ticker'] = ticker
#                         request.session['start_time'] = start_time.strftime('%Y-%m-%dT%H:%M:%S')
#                         request.session['end_time'] = end_time.strftime('%Y-%m-%dT%H:%M:%S')
#                         context = {'result': backtest_summary_show.to_html(index=False, na_rep=''),
#                                    'ticker': ticker,
#                                    'start_time': start_time,
#                                    'end_time': end_time,
#                                    }
#
#                         #backtest_summary.to_csv(f'/Users/jingnie/startup/eshujupai-reports/{ticker}_{end_time.date()}.csv')
#                         html_string = render_to_string('predictapp/backtest_private.html', context)
#                         with open(f'/Users/jingnie/startup/eshujupai-reports/backtest/{end_time.date()}_{ticker}.html', 'w') as html_file:
#                             html_file.write(html_string)
#
#                         app.update_and_new(ticker=ticker, action=best_strategy['predict_signal'], qty=100,
#                                            limit_price=best_strategy['limit_price'],
#                                            take_profit=best_strategy['predict_take_profit'],
#                                            stop_loss=best_strategy['predict_stop_loss'],
#                                           )
#                 # app.disconnect()
#                 return render(request, 'predictapp/backtest_private.html', context)
#                 # todo: delete this for block, it is for paper account --- end
#         else:
#             form = UploadForm()
#         return render(request, 'predictapp/upload_historical_data.html',
#                       {'form': form})
#     except:
#         log.error(traceback.print_exc())
#         return render(request, '404.html',
#                       {'error': _('Failed to run the backtest. Please upload the file with historical data.')})
