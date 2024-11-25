from django.shortcuts import render, redirect
from web import settings
from predict.settings import PRIVATE_STRATEGY_RANK
from predictapp.models_operation import (
    get_userpayment,
    set_userpayment
)
from django.utils.translation import gettext_lazy as _
from .views import get_saved_result, format_backtest_summary
from urllib.parse import parse_qs
import stripe
from utils.alipay import AliPay
import time
import logging
import traceback


log = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.log = 'debug'

def response_after_paid(request, set_payment=True):
    try:
        # The payment was successfully processed, the user's card was charged.
        user_payment = set_userpayment(request.user) if set_payment else get_userpayment(request.user)

        # Redirect the user to 'backtest_private.html' to show all backtest results
        backtest_summary, backtest_detail, ticker, start_time, end_time, _ = get_saved_result(request)
        backtest_summary_show = format_backtest_summary(request, backtest_summary)
        return render(request, 'predictapp/backtest_private.html',
                      {'result': backtest_summary_show.to_html(index=False, na_rep=''),
                       'ticker': ticker, 'start_time': start_time, 'end_time': end_time})
    except:
        # if user_payment is None:
        #     user_payment = get_userpayment(request.user)
        return render(request, 'predictapp/payment.html', {'user_payment': user_payment})

def payment(request):
    user_payment, is_paid = get_userpayment(request.user)
    context = {"stripe_public_key": settings.STRIPE_PUBLIC_KEY,
               "user_payment": user_payment}
    return render(request, "predictapp/payment.html", context)

def stripe_checkout(request):
    # Test card: https://stripe.com/docs/testing
    # Visa: 4242424242424242. Mastercard: 5555555555554444. American Express: 3782 822463 10005
    # Set your secret key: remember to change this to your live secret key in production
    # See your keys here: https://dashboard.stripe.com/account/apikeys
    # Token is created using Checkout or Elements!
    # Get the payment token ID submitted by the form:
    try:
        if request.method == "POST":
            token = request.POST.get("stripeToken")
            if request.LANGUAGE_CODE == 'zh-cn':
                charge = stripe.Charge.create(
                    amount      = settings.STRIPE_PRICE_CNY,  # Chinese CNY 49.99
                    currency    = "cny",
                    source      = token,
                    description = "数据派 30天费用",
                    statement_descriptor='eShuJuPai',
                )
            else:
                charge = stripe.Charge.create(
                    amount      = settings.STRIPE_PRICE_USD, # USD 7.99
                    currency    = "usd",
                    source      = token,
                    description = "eShuJuPai 30 days payment",
                    statement_descriptor='eShuJuPai',
                )
            return response_after_paid(request)
    except Exception as err:
        log.error(traceback.print_exc())
        return render(request, '404.html', {'error': _('Failed to pay')})

def get_alipay_settings(debug=True):
    '''
    Return the Alipay settings for the specific environment.
    :param debug: bool, PROD environment if False; Sandbox environment if True
    :return: return ROD settings if False; Sandbox settings if True
    '''
    if debug:
        # 商户app_id
        app_id = settings.ALIPAY_APP_ID_DEBUG  # 复制来自支付宝生成的id
        # 服务器异步通知页面路径 需http: // 格式的完整路径，不能加?id = 123 这类自定义参数，必须外网可以正常访问
        # 发post请求
        notify_url = "http://127.0.0.1:8000/payment/alipay_notify"  # 将这两个链接复制到支付宝中

        # 页面跳转同步通知页面路径 需http: // 格式的完整路径，不能加?id = 123 这类自定义参数，必须外网可以正常访问
        # 发get请求
        return_url = "http://127.0.0.1:8000/payment/alipay_return"
    else:
        app_id = settings.ALIPAY_APP_ID
        # set return and notify url to the prod server
        notify_url = '{host}/payment/alipay_notify'.format(host=settings.SERVER_HOST)
        return_url = '{host}/payment/alipay_return'.format(host=settings.SERVER_HOST)
    return app_id, notify_url, return_url

def ali():
    '''
    Test passowrd: 1111111
    :return:
    '''
    debug = settings.DEBUG
    app_id, notify_url, return_url = get_alipay_settings(debug)

    # 商户私钥路径
    app_private_key_path = "keys/pri"   #设置公钥和私钥的地址，文件上下两行begin和end是必须的，公钥就放在第二行。
    # 支付宝公钥路径
    alipay_public_key_path = "keys/pub"

    alipay = AliPay(
        appid=app_id,
        app_notify_url=notify_url,
        return_url=return_url,
        app_private_key_path=app_private_key_path,
        alipay_public_key_path=alipay_public_key_path,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥
        debug=debug,  # 默认False,
    )
    return alipay

def alipay_checkout(request):
    try:
        if request.method == "GET":
            return render(request, 'predictapp/payment.html')
        else:
            if request.LANGUAGE_CODE == 'zh-cn':

                alipay = ali()
                # 生成支付的url
                pay_url= alipay.direct_pay(
                    subject="数据派",  # 商品简单描述
                    out_trade_no=f"SJP_{time.time()}",  # 商户订单号
                    total_amount=settings.ALIPAY_PRICE_CNY,  # 交易金额(单位: 元 保留俩位小数)
                    # body=_("数据派 30 days payment"),  # 订单描述、订单详细、订单备注，显示在支付宝收银台里的“商品描述”里
                )

                # pay_url = "https://openapi.alipaydev.com/gateway.do?{}".format(query_params)
                return redirect(pay_url)
            else:
                stripe.api_key = "sk_test_8mA1baNCjkae17YkMoRebHXu"

                stripe.Source.create(
                    type='ach_credit_transfer',
                    currency='usd',
                    amount='799',
                    # redirect={
                    # return_url: 'http://www.edatapai.com/payment',
                    # },
                    owner={
                        'email': 'shujupai@gmail.com'
                    }
                )
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html', {'error': _('Failed to proceed Alipay')})

def alipay_notify(request):
    try:
        if request.method == "POST":
            # 检测是否支付成功

            alipay = ali()
            # request.body                  => 字节类型
            # request.body.decode('utf-8')  => 字符串类型
            """
            {"k1":["v1"],"k2":["v1"]}
            k1=[v1]&k2=[v2]
            """
            body_str = request.body.decode('utf-8')
            post_data = parse_qs(body_str)
            # {k1:[v1,],k2:[v2,]}

            # {k1:v1}
            post_dict = {}
            for k, v in post_data.items():
                post_dict[k] = v[0]

            print('post_dict: ', post_dict)
            """
            {'gmt_create': '2017-11-24 14:53:41', 'charset': 'utf-8', 'gmt_payment': '2017-11-24 14:53:48', 'notify_time': '2017-11-24 14:57:05', 'subject': '充气式韩红', 'sign': 'YwkPI9BObXZyhq4LM8//MixPdsVDcZu4BGPjB0qnq2zQj0SutGVU0guneuONfBoTsj4XUMRlQsPTHvETerjvrudGdsFoA9ZxIp/FsZDNgqn9i20IPaNTXOtQGhy5QUetMO11Lo10lnK15VYhraHkQTohho2R4q2U6xR/N4SB1OovKlUQ5arbiknUxR+3cXmRi090db9aWSq4+wLuqhpVOhnDTY83yKD9Ky8KDC9dQDgh4p0Ut6c+PpD2sbabooJBrDnOHqmE02TIRiipULVrRcAAtB72NBgVBebd4VTtxSZTxGvlnS/VCRbpN8lSr5p1Ou72I2nFhfrCuqmGRILwqw==', 'buyer_id': '2088102174924590', 'invoice_amount': '666.00', 'version': '1.0', 'notify_id': '11aab5323df78d1b3dba3e5aaf7636dkjy', 'fund_bill_list': '[{"amount":"666.00","fundChannel":"ALIPAYACCOUNT"}]', 'notify_type': 'trade_status_sync', 'out_trade_no': 'x21511506412.4733646', 'total_amount': '666.00', 'trade_status': 'TRADE_SUCCESS', 'trade_no': '2017112421001004590200343962', 'auth_app_id': '2016082500309412', 'receipt_amount': '666.00', 'point_amount': '0.00', 'app_id': '2016082500309412', 'buyer_pay_amount': '666.00', 'sign_type': 'RSA2', 'seller_id': '2088102172939262'}
            {'stade_status': "trade_success",'order':'x2123123123123'}
            """
            # app_id
            app_id = post_dict['app_id']
            total_amount = float(post_dict['total_amount'])
            # 商户网站订单号
            out_trade_no = post_dict['out_trade_no']
            # 支付宝单号
            trade_no = post_dict['trade_no']
            # 返回支付状态
            trade_status = post_dict['trade_status']
            print(f'alipay_notify: {trade_status}_{trade_no}_{out_trade_no}_{total_amount}')
            log.info(f'alipay_notify: {trade_status}_{trade_no}_{out_trade_no}_{total_amount}')

            sign = post_dict.pop('sign', None)
            status = alipay.verify(post_dict, sign)
            print('alipay notify: POST verify: ', status)
            print('total_amount-settings.ALIPAY_PRICE_CNY=', (total_amount - settings.ALIPAY_PRICE_CNY))
            if status:
                print(post_dict['trade_status'])
                print(post_dict['out_trade_no'])
                app_id_settings, _, _ = get_alipay_settings(settings.DEBUG)
                if app_id == app_id_settings and abs(total_amount-settings.ALIPAY_PRICE_CNY) < 1e-6:
                    return response_after_paid(request, set_payment=False)
            else:
                # 黑客攻击
                print(f'alipay_notify: Hacked: {trade_status}_{trade_no}_{out_trade_no}_{total_amount}')
                log.error(f'alipay_notify: Hacked: {trade_status}_{trade_no}_{out_trade_no}_{total_amount}')
            return response_after_paid(request, set_payment=False)
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html', {'error': _('Failed to pay.')})

def alipay_return(request):
    try:
        if request.method == "GET":
            # http://127.0.0.1:8000/payment/alipay_return?charset=utf-8&out_trade_no=SJP_1538039206.9089468&method=alipay.trade.page.pay.return&total_amount=59.99&sign=a%2FY64O5uUGduu6Pbt7onj8PVVibY9FY3AmgVyjaK5wdrxhoSbDQy9UV1Qwffll1J8GVN8CObSKWz2I0wsOCGMjEPOsUXoYt%2BuzQ6SBuwPCX27i2tjT%2FaR8wtngo8fV2BC5RbZEfa6ftblh7Z3xROiZ391auHNWjg8PgGMaBAFqYuSRg8N%2FvpoLrTXQbkXSZ0mbnEySoMsqBVpv4WNQD%2F3S28PB893se8Mu3nURrdtJJUiXA1H8lQ0e9vZHK8WSBL215SnU3bLlD2zybQfJlFEOWeZOKQ2JabaWDK6v6jnZPoyL7yMh58poBZsjQkYGYymzsweOz2gyrF%2FXKk%2BKIoyg%3D%3D&trade_no=2018092721001004990500282616&auth_app_id=2016091600528115&version=1.0&app_id=2016091600528115&sign_type=RSA2&seller_id=2088102175955522&timestamp=2018-09-27+17%3A08%3A27
            # QueryDict = {'k':[1],'k1':[11,22,3]}
            alipay = ali()
            '''
            {'charset': 'utf-8', 'out_trade_no': 'SJP_1538147787.7482011', 'method': 'alipay.trade.page.pay.return', 'total_amount': '59.99',
             'sign': 'H51SpIrA9srcz0QZ2xfytXVuwt3uahPEZ7h7H757AGLxGzNWGEnz3qhpsyA21WtpgPeLJp0ultUePhvj24XCqupDOK6ftc3A4VFma4Ty2iauRqYWXZjUUi7cWAOHApgPqeYp9o+WkTpJZFZAXitIA6AqngPcBmCO/COn9MWsXiy9x14Ur0y5p3Ed+b+pMr5Cb3T5Jd+H/1gfpi70agaJisnxejkYwbo4UemnRXE/g6TUgsaRtlFVUrjWk608sXEjycoOfGj9KqBIg8pgXzskaAQ7a1fFiyA7zq/L6+UJ1bbad1z1D8AiiCMvX7aiCw+Z1mU23NqY07z72tjq06e+hg==',
             'trade_no': '2018092821001004990500286882', 'auth_app_id': '2016091600528115', 'version': '1.0',
             'app_id': '2016091600528115', 'sign_type': 'RSA2', 'seller_id': '2088102175955522',
             'timestamp': '2018-09-28 23:17:16'}
            '''
            params = request.GET.dict()
            # app_id
            app_id = params['app_id']
            total_amount = float(params['total_amount'])
            # 商户网站订单号
            out_trade_no = params['out_trade_no']
            # 支付宝单号
            trade_no = params['trade_no']
            # 返回支付状态
            # trade_status = params['trade_status']
            print(f'alipay_return: {trade_no}_{out_trade_no}_{total_amount}')
            log.info(f'alipay_return: {trade_no}_{out_trade_no}_{total_amount}')

            sign = params.pop('sign', None)
            status = alipay.verify(params, sign)
            print('alipay_return: GET verify: ', status)
            # if status:
            #     if app_id == settings.ALIPAY_APP_ID and rade_status == 'TRADE_SUCCESS':
            print('total_amount-settings.ALIPAY_PRICE_CNY=', (total_amount - settings.ALIPAY_PRICE_CNY))
            app_id_settings, _, _ = get_alipay_settings(settings.DEBUG)
            if app_id == app_id_settings and abs(total_amount - settings.ALIPAY_PRICE_CNY) < 1e-6:
                return response_after_paid(request, set_payment=True)
            else:
                # 黑客攻击
                print(f'alipay_return: Hacked: {trade_no}_{out_trade_no}_{total_amount}')
                log.error(f'alipay_return: Hacked: {trade_no}_{out_trade_no}_{total_amount}')

                query_url = alipay.trade_query(out_trade_no, trade_no)
                response = redirect(query_url)
                print(response)
            return response_after_paid(request, set_payment=False)
        #     '''
        #     {"alipay_trade_query_response": {"code": "10000", "msg": "Success", "buyer_logon_id": "uyj***@sandbox.com",
        #                                      "buyer_pay_amount": "0.00", "buyer_user_id": "2088102176530997",
        #                                      "buyer_user_type": "PRIVATE", "invoice_amount": "0.00",
        #                                      "out_trade_no": "SJP_1538148136.5333846", "point_amount": "0.00",
        #                                      "receipt_amount": "0.00", "send_pay_date": "2018-09-28 23:23:12",
        #                                      "total_amount": "59.99", "trade_no": "2018092821001004990500286702",
        #                                      "trade_status": "TRADE_SUCCESS"},
        #      "sign": "d0oMEz8QjjHuSLJrPQYcMJjCugFSx0iDpLav9GQpFk60BvDSVifJMsDC32tnOac7cZ9o70kglyPiA5VTbupO/Vqj76mjqCyAQmuyo6CYmkYDB8OasBJjmyis5Dyb9wFh9SMWQL3lOUYff0dTGtk0r+hj31btkIJle/PoPeReqdBPzYC7A+IZPE55aEnMxPM5FOqipNVkw2ivAi7haht2WO/BSDkDssU9VnVM9ZlPC5O7HhU1uPXf6u09uUGLK1qDWdJSRFQXLuF75pkJd41Zdiy0ADrKPLjrNkOcs6lehSmE6ZPoEwYkPQJBh016OTbMaaHIaQOk5i1hR28ntSy62Q=="}
        #     '''
        #     '''
        #     # code 40004 支付订单未创建
        #     # code 10000 trade_status  WAIT_BUYER_PAY  等待支付
        #     # oode 10000 trade_status  TRADE_SUCCESS  支付成功
        #     # response 是字典
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html', {'error': _('Failed to pay')})

def wechat_checkout(request):
    try:
        if request.method == "POST":
            return render(request, 'checkout_wechat.html')
        return render(request, 'predictapp/payment.html')
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html', {'error': _('Failed to proceed WeChat Pay')})

def zhifubao_checkout(request):
    try:
        if request.method == "POST":
            return render(request, 'checkout_zhifubao.html')
        return render(request, 'predictapp/payment.html')
    except:
        log.error(traceback.print_exc())
        return render(request, '404.html', {'error': _('Failed to proceed WeChat Pay')})
