from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta, timezone
import pytz
from jsonfield import JSONField
import logging


log = logging.getLogger(__name__)

class Upload(models.Model):
    '''
    A typical class defining a model, derived from the Model class.
    '''
    # Fields
    ticker = models.CharField(verbose_name=_('Ticker'), max_length=64, blank=False, null=False, default='us30')
    commission = models.FloatField(verbose_name=_('Commission'), blank=True, null=True, default=0.00, help_text=_('per share'))
    document = models.FileField(verbose_name=_('Historical data (Option)'), upload_to='documents/', blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Metadata
    class Meta:
        ordering = ['-uploaded_at', 'ticker']

    def __str__(self):
        """String for representing the MyModelName object (in Admin site etc.)."""
        return f'{self.ticker}_{self.commission}_{self.document}_{self.uploaded_at}'

    # Methods
    def get_absolute_url(self):
        """Returns the url to access a particular instance of MyModelName."""
        return reverse('upload-detail-view', args=[str(self.id)])

class Strategy(models.Model):
    '''
    Trading strategy
    '''
    #Fields
    strategy = models.CharField(max_length=64, blank=False, null=False)
    description = models.TextField(blank=True)
    parameters = JSONField()

class Exchange(models.Model):
    '''
    Listing exchanges
    '''
    code = models.CharField(max_length=16, blank=False, null=False, primary_key=True)
    name = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=16, blank=True)
    timezone = models.CharField(max_length=16, blank=True) # pytz value
    open_time = models.DateTimeField(blank=True, null=True)
    close_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['country', 'code']

    def __str__(self):
        """String for representing the MyModelName object (in Admin site etc.)."""
        return f'{self.code}_{self.country}'

class Index(models.Model):
    '''
    A typical class defining a model, derived from the Model class.
    e.g: 沪深300
    '''
    # Fields
    symbol = models.CharField(max_length=16, blank=False, null=False, primary_key=True)
    name = models.CharField(max_length=64, blank=False, null=False)
    # List of securities in the Index
    tickers = JSONField(blank=True, null=True)
    note = models.CharField(max_length=128, blank=True, null=True)

    # Metadata
    class Meta:
        ordering = ['symbol']

    def __str__(self):
        """String for representing the MyModelName object (in Admin site etc.)."""
        return f'{self.name}'

class Security(models.Model):
    '''
    A typical class defining a model, derived from the Model class.
    '''
    # Fields
    ticker = models.CharField(max_length=64, blank=False, null=False, primary_key=True)
    # exchange = models.OneToOneField(Exchange, on_delete=models.CASCADE, blank=True)
    exchange = models.CharField(max_length=16, blank=True, null=True)
    asset_type = models.CharField(max_length=32, blank=True, null=True)
    currency = models.CharField(max_length=8, blank=True, null=True)
    volume = models.FloatField(blank=True, null=True)
    name = models.CharField(max_length=64, blank=True, null=True)
    index = models.ManyToManyField(Index)
    note = models.CharField(max_length=128, blank=True, null=True)

    # Metadata
    class Meta:
        ordering = ['-volume', 'ticker']

    def __str__(self):
        """String for representing the MyModelName object (in Admin site etc.)."""
        return f'{self.ticker}_{self.exchange}_{self.asset_type}_{self.currency}_{self.name}'

class BacktestCondition(models.Model):
    '''
       A list of strategies with backtest and predicted results , ranking by 'return_rate' in the backtest.
       '''
    # Fields
    security = models.ForeignKey(Security, on_delete=models.CASCADE, blank=False, null=False)
    start_time = models.DateTimeField(blank=False, null=False)
    end_time = models.DateTimeField(blank=False, null=False)
    open_price = models.FloatField(blank=True, null=True)
    close_price = models.FloatField(blank=True, null=True)
    # The backtest result of top 1 return_rate strategy
    strategy = models.CharField(max_length=64, blank=True, null=True)
    commission = models.FloatField(blank=True, null=True)
    profit_factor = models.FloatField(blank=True, null=True)
    loss_factor = models.FloatField(blank=True, null=True)
    total_return = models.FloatField(blank=True, null=True)
    return_rate = models.FloatField(blank=True, null=True)
    sharpe = models.FloatField(blank=True, null=True)
    drawdown = models.FloatField(blank=True, null=True)
    volatility = models.FloatField(blank=True, null=True)

    # Metadata
    class Meta:
        ordering = ['security', '-end_time', 'start_time']
        unique_together = (('security', 'start_time', 'end_time'),)

    def __str__(self):
        """String for representing the MyModelName object (in Admin site etc.)."""
        return f'{self.security}_{self.start_time.date()}_{self.end_time.date()}_{self.return_rate}'

    def get_absolute_url(self):
        """Returns the url to access a particular instance of the model."""
        return reverse('backtestcondition-detail-view', args=[str(self.id)])

class BacktestSummary(models.Model):
    '''
       A list of strategies with backtest and predicted results , ranking by 'return_rate' in the backtest.
       '''
    # Fields
    # summary is BACKTEST_OUTPUT_COLUMNS = ['strategy', 'commission', 'profit_factor', 'loss_factor', 'total_return', 'return_rate',
    #                            'sharpe', 'drawdown', 'volatility', 'predict_signal', 'limit_price', 'predict_take_profit', 'predict_stop_loss']
    backtest_condition = models.OneToOneField(BacktestCondition, on_delete=models.CASCADE, blank=False, null=False, primary_key=True)
    summary = JSONField(null=True)

    def __str__(self):
        """String for representing the MyModelName object (in Admin site etc.)."""
        return f'{self.backtest_condition}'

    def get_absolute_url(self):
        """Returns the url to access a particular instance of the model."""
        return reverse('backtestsummary-detail-view', args=[str(self.pk)])

class BacktestDetail(models.Model):
    '''
    Backtest details
    '''
    # Fields
    backtest_condition = models.OneToOneField(BacktestCondition, on_delete=models.CASCADE, blank=False, null=False, primary_key=True)
    detail = JSONField(null=True)

    def __str__(self):
        """String for representing the MyModelName object (in Admin site etc.)."""
        return f'{self.backtest_condition}'

    def get_absolute_url(self):
        """Returns the url to access a particular instance of the model."""
        return reverse('backtestdetail-detail-view', args=[str(self.pk)])





