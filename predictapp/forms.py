from django import forms
from predictapp.models import (
    Upload,
    UserPayment,
    Strategy,
    Index,
    Security,
    BacktestCondition,
    BacktestSummary,
    BacktestDetail
)


class UploadForm(forms.ModelForm):
    class Meta:
        model = Upload
        fields = ('ticker', 'commission', 'document')
        # labels = {'ticker': _('Ticker*'),
        #           'commission': _('Commission'),
        #           'document': _('Document(option)')
        #           }

    def __init__(self, *args, **kwargs):
        super(UploadForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(UploadForm, self).save(commit=False)
        if commit:
            instance.save()
        return instance

class UserPaymentForm(forms.ModelForm):
    class Meta:
        model = UserPayment
        fields = ('user', 'payment_time', 'expiry_time', 'is_paid')

    def __init__(self, *args, **kwargs):
            self.user = kwargs.pop('user')
            self.is_paid = kwargs.pop('is_paid')
            super(UserPaymentForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(UserPaymentForm, self).save(commit=False)
        instance.user = self.user
        instance.is_paid = self.is_paid
        if commit:
            instance.save()
        return instance

class StrategyForm(forms.ModelForm):
    class Meta:
        model = Strategy
        fields = ('strategy', 'description', 'parameters')

    def __init__(self, *args, **kwargs):
            self.strategy = kwargs.pop('strategy')
            super(StrategyForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(StrategyForm, self).save(commit=False)
        instance.strategy = self.strategy
        if commit:
            instance.save()
        return instance

class IndexForm(forms.ModelForm):
    class Meta:
        model = Index
        fields = ('symbol', 'name', 'tickers')

    def __init__(self, *args, **kwargs):
        self.symbol = kwargs.pop('symbol')
        self.name = kwargs.pop('name')
        self.tickers = kwargs.pop('tickers')
        super(SecurityForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(IndexForm, self).save(commit=False)
        instance.symbol = self.symbol
        if commit:
            instance.save()
        return instance

class SecurityForm(forms.ModelForm):
    class Meta:
        model = Security
        fields = ('ticker', 'exchange', 'asset_type', 'currency', 'volume', 'name', 'note')

    def __init__(self, *args, **kwargs):
            self.ticker = kwargs.pop('ticker')
            super(SecurityForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(SecurityForm, self).save(commit=False)
        instance.ticker = self.ticker
        if commit:
            instance.save()
        return instance

class BacktestConditionForm(forms.ModelForm):
    class Meta:
        model = BacktestCondition
        fields = ('security', 'start_time', 'end_time', 'strategy', 'commission', 'profit_factor', 'loss_factor',
        'total_return', 'return_rate', 'sharpe', 'drawdown', 'volatility')

    def __init__(self, *args, **kwargs):
        self.security = kwargs.pop('security')
        self.start_time = kwargs.pop('start_time')
        self.end_time = kwargs.pop('end_time')
        self.strategy = kwargs.pop('strategy')
        self.commission = kwargs.pop('commission')
        self.profit_factor = kwargs.pop('profit_factor')
        self.loss_factor = kwargs.pop('loss_factor')
        self.total_return = kwargs.pop('total_return')
        self.return_rate = kwargs.pop('return_rate')
        self.sharpe = kwargs.pop('sharpe')
        self.drawdown = kwargs.pop('drawdown')
        self.volatility = kwargs.pop('volatility')
        super(BacktestConditionForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(BacktestConditionForm, self).save(commit=False)
        instance.security = self.security
        instance.start_time = self.start_time
        instance.end_time = self.end_time
        instance.strategy = self.strategy
        instance.commission = self.commission
        instance.profit_factor = self.profit_factor
        instance.loss_factor = self.loss_factor
        instance.total_return = self.total_return
        instance.return_rate = self.return_rate
        instance.sharpe = self.sharpe
        instance.drawdown = self.drawdown
        instance.volatility = self.volatility
        if commit:
            instance.save()
        return instance

class BacktestSummaryForm(forms.ModelForm):
    class Meta:
        model = BacktestSummary
        fields = ('backtest_condition', 'summary')

    def __init__(self, *args, **kwargs):
        self.backtest_condition = kwargs.pop('backtest_condition')
        super(BacktestSummaryForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(BacktestSummaryForm, self).save(commit=False)
        if commit:
            instance.backtest_condition = self.backtest_condition
            instance.save()
        return instance

class BacktestDetailForm(forms.ModelForm):
    class Meta:
        model = BacktestDetail
        fields = ('backtest_condition', 'detail')

    def __init__(self, *args, **kwargs):
            super(BacktestDetailForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(BacktestDetailForm, self).save(commit=False)
        if commit:
            instance.save()
        return instance
