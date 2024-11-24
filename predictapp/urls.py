from django.urls import path
from . import views
from . import views_pay


urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_historical_data, name='upload'),
    path('upload/poll_state', views.poll_state, name='poll_state'),
    path('backtest_table/', views.backtest_table, name='backtest_table'),
    path('backtest_figure/', views.backtest_figure, name='backtest_figure'),

    # Payment
    path('payment/', views_pay.payment, name='payment'),
    path('payment/stripe_checkout', views_pay.stripe_checkout, name="stripe_checkout"),  # Stripe Checkout
    path('payment/alipay_checkout', views_pay.alipay_checkout, name='alipay_checkout'), # Alipay
    path('payment/alipay_notify', views_pay.alipay_notify, name='alipay_notify'),  # Alipay
    path('payment/alipay_return', views_pay.alipay_return, name='alipay_return'), # Alipay
    path('alipay_checkout', views_pay.alipay_checkout, name='alipay_checkout'),  # Alipay
    path('payment/wechat_checkout', views_pay.wechat_checkout, name='wechat_checkout'),  # wechat pay-QR code
    path('wechat_checkout', views_pay.wechat_checkout, name='wechat_checkout'),  # wechat pay-QR code
    path('payment/zhifubao_checkout', views_pay.zhifubao_checkout, name='zhifubao_checkout'),  # Alipay-QR code
    path('zhifubao_checkout', views_pay.zhifubao_checkout, name='zhifubao_checkout'),  # Alipay-QR code

    # Export from database
    path('export/security', views.export_security, name='export_security'),

    # Research reports
    path('reports/', views.reports, name='reports'),
]
