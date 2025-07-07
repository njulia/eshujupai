from django.contrib import admin
# from django.contrib.auth.models import User, Group
from .models import (
    Upload,
    Strategy,
    Exchange,
    Index,
    Security,
    BacktestCondition,
    BacktestSummary,
    BacktestDetail,
)
from .models_operation import delete_backtest, import_exchanges, import_securities, import_indexes, get_backtest
from predictapp.tasks import run_bulk_backtest_multithread_task, run_bulk_backtest_singlethread_task, get_backtest_task_asyn
from predict.settings import BACKTEST_SET
from utils.settings_index import BACKTEST_REPORT_STRATEGY_RANK, BACKTEST_REPORT_SECURITIES
from utils.report import get_top_securities, get_interactive_chart, get_static_chart
from predict.utils.scanner import calc_stats, zhangting_scanner
from utils.settings_index import indexes
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from django.shortcuts import render
from django.template.loader import render_to_string
from datetime import date
import json
import logging
import traceback


log = logging.getLogger(__name__)

# class UserResource(resources.ModelResource):
#     class Meta:
#         model = User
#
# class UserAdmin(ImportExportModelAdmin):
#     resource_class = UserResource
#
# class GroupResource(resources.ModelResource):
#     class Meta:
#         model = Group
#
# class GroupAdmin(ImportExportModelAdmin):
#     resource_class = GroupResource

class UploadResource(resources.ModelResource):
    class Meta:
        model = Upload

class UploadAdmin(ImportExportModelAdmin):
    resource_class = UploadResource

class StrategyResource(resources.ModelResource):
    class Meta:
        model = Strategy

class StrategyAdmin(ImportExportModelAdmin):
    resource_class = StrategyResource

class ExchangeResource(resources.ModelResource):
    class Meta:
        model = Exchange

class ExchangeAdmin(ImportExportModelAdmin):
    resource_class = ExchangeResource
    actions = ['import_exchanges', 'delete_backtest', 'run_backtest_multithread', 'run_backtest_singlethread',
               'create_report_static', 'create_report_interactive']

    def import_exchanges(self, request, queryset):
        log.info(f'Admin Import exchanges')
        import_exchanges()

    def delete_backtest(self, request, queryset):
        for exchange in queryset:
            log.info(f'Admin Delete backtest: {exchange} ')
            delete_backtest(exchanges=[exchange.code])

    def run_backtest_multithread(self, request, queryset):
        for exchange in queryset:
            log.info(f'Admin Run bulk backtest multi-threading asynchronous: {exchange}')
            run_bulk_backtest_multithread_task.delay(exchanges=[exchange.code])

    def run_backtest_singlethread(self, request, queryset):
        for exchange in queryset:
            log.info(f'Admin Run bulk backtest single-threading asynchronous: {exchange}')
            run_bulk_backtest_singlethread_task.delay(exchanges=[exchange.code])

    def create_report_static(self, request, queryset):
        log.info(f'Admin create static report for exchange')
        try:
            exchanges = []
            for exchange in queryset:
                exchanges.append(exchange.code)
            topn, tickers, table = get_top_securities(n=BACKTEST_REPORT_SECURITIES, exchanges=exchanges)
            results = get_static_chart(request, tickers)

            context = {'index': exchanges,
                       'n': len(tickers),
                       'results': results,
                       'backtest_set': BACKTEST_SET,
                       'strategy_rank': BACKTEST_REPORT_STRATEGY_RANK,
                       'tables': (table,),
                      }
            return render(request, 'predictapp/backtest_report_static.html', context)
        except:
            log.error(traceback.print_exc())
            return render(request, '404.html', {'error': 'Failed to create static report'})

    def create_report_interactive(self, request, queryset):
        log.info(f'Admin create interactive report for exchange')
        try:
            exchanges = []
            for exchange in queryset:
                exchanges.append(exchange.code)

            topn, tickers, _ = get_top_securities(n=BACKTEST_REPORT_SECURITIES, exchanges=exchanges)
            results = get_interactive_chart(request, tickers)

            context = {'index': exchanges,
                       'n': len(tickers),
                       'topn': topn,
                       'results': results,
                       'backtest_set': BACKTEST_SET,
                       'strategy_rank': BACKTEST_REPORT_STRATEGY_RANK,
                      }
             # Save report to html file
            content = render_to_string('predictapp/backtest_report_interactive.html', context)
            path = 'static/reports/{0}_{1}.html'.format(date.today(), exchanges)
            with open(path, 'w') as static_file:
                static_file.write(content)
            return render(request, 'predictapp/backtest_report_interactive.html', context)
        except:
            log.error(traceback.print_exc())
            return render(request, '404.html', {'error': 'Failed to create interactive report'})

    import_exchanges.short_description = 'Import all exchanges'
    delete_backtest.short_description = 'Delete backtest of selected exchange'
    run_backtest_multithread.short_description = 'Run backtest multi-threading'
    run_backtest_singlethread.short_description = 'Run backtest single-threading'
    create_report_static.short_descriptionn = 'Create report static'
    create_report_interactive.short_description = 'Create report interactive'

class SecurityResource(resources.ModelResource):
    class Meta:
        model = Security
        fields = ('ticker', 'exchange', 'asset_type', 'currency', 'volume', 'name')
        export_order = ('ticker', 'exchange', 'asset_type', 'currency', 'volume', 'name')
        # exclude = ('volume',)
        # import_id_fields = ('ticker',)
        # skip_unchanged = True
        # report_skipped = True

class SecurityAdmin(ImportExportModelAdmin):
    resource_class = SecurityResource
    actions = ['get_stats', 'run_backtest', 'run_backtest_backend_daily', 'run_backtest_backend_weekly', 'run_backtest_backend_monthly',
               'import_securities', 'create_report',
               'create_report_topn_static', 'create_report_hs300_static', 'create_report_dow30_static',
               'create_report_topn', 'create_report_xq10like', 'create_report_shg50', 'create_report_hs300', 'create_report_dow30']
    search_fields = ['ticker', 'exchange', 'asset_type']

    def get_stats(self, request, queryset):
        log.info(f'Admin get statstics for security')
        for security in queryset:
            calc_stats(security.ticker)

    def run_backtest(self, request, queryset):
        log.info(f'Admin run backbest for security synchronized')
        for security in queryset:
            get_backtest(security.ticker)

    def run_backtest_backend_daily(self, request, queryset):
        log.info(f'Admin run backtest backend daily for security')
        for security in queryset:
            print(f'Run backtest daily Security: {security.index}')
            get_backtest_task.delay(security.ticker)

    def run_backtest_backend_weekly(self, request, queryset):
        log.info(f'Admin run backtest backend weekly for security')
        for security in queryset:
            print(f'Run backtest weekly Security: {security.index}')
            get_backtest_task.delay(security.ticker, period='W')

    def run_backtest_backend_monthly(self, request, queryset):
        log.info(f'Admin run backtest backend monthly for security')
        for security in queryset:
            print(f'Run backtest monthly Security: {security.index}')
            get_backtest_task.delay(security.ticker, period='M')

    def import_securities(self, request, queryset):
        log.info('Admin Import securities')
        import_securities()

    def create_report(self, request, queryset):
        log.info(f'Admin Create report for selected securities')
        tickers = (security.ticker for security in queryset)
        results = get_interactive_chart(request, tickers)

        context = {'results': results,
                   'backtest_set': BACKTEST_SET,
                   'strategy_rank': BACKTEST_REPORT_STRATEGY_RANK,
                   }
        return render(request, 'predictapp/backtest_report_interactive.html', context)

    def _create_report_static(self, request, index_key=None, n=BACKTEST_REPORT_SECURITIES, lang='zh'):
        '''
                Create report for the index
                :param request:
                :param index_key: string, namedtuple defined in setting_index.py
                :param n: integer. Top n result
                :return: context for html webpage of report
                '''
        try:
            log.info(f'Admin Create static report for {index_key}')
            if index_key:
                index = indexes[index_key]
                topn, tickers, table = get_top_securities(n=n, securities=index.index_tickers, lang=lang)
            else:
                topn, tickers, table = get_top_securities(n=n, lang=lang)
            results = get_static_chart(request, tickers)

            context = {'index': index.index_name if index_key else '沪深A股',
                       'n': len(tickers),
                       'results': results,
                       'backtest_set': BACKTEST_SET,
                       'strategy_rank': BACKTEST_REPORT_STRATEGY_RANK,
                       'tables': (table,),
                       }
            return context
        except:
            log.error(traceback.print_exc())
            return None

    def create_report_topn_static(self, request, queryset):
        context = self._create_report_static(request, index_key=None, n=100)
        return render(request, 'predictapp/backtest_report_static.html', context)

    def create_report_shg50_static(self, request, queryset):
        context = self._create_report_static(request, 'SHG-50', n=50)
        return render(request, 'predictapp/backtest_report_static.html', context)

    def create_report_hs300_static(self, request, queryset):
        context = self._create_report_static(request, 'HS-300', n=50)
        return render(request, 'predictapp/backtest_report_static.html', context)

    def create_report_dow30_static(self, request, queryset):
        context = self._create_report_static(request, 'DOW-30', n=30, lang='en')
        return render(request, 'predictapp/backtest_report_static_en.html', context)

    def _create_report_interactive(self, request, index_key=None, n=BACKTEST_REPORT_SECURITIES):
        '''
        Create report for the index
        :param request:
        :param index_key: string, namedtuple defined in setting_index.py
        :param n: integer. Top n result
        :return: context for html webpage of report
        '''
        try:
            log.info(f'Admin Create interactive report for {index_key}')
            if index_key:
                index = indexes[index_key]
                topn, tickers, _ = get_top_securities(n=n, securities=index.index_tickers)
            else:
                topn, tickers, _ = get_top_securities(n=n)
            results = get_interactive_chart(request, tickers)

            context = {'index': index.index_name if index_key else '沪深A股',
                       'n': len(tickers),
                       'topn': topn,
                       'results': results,
                       'backtest_set': BACKTEST_SET,
                       'strategy_rank': BACKTEST_REPORT_STRATEGY_RANK,
                       }
            # Save report to html file
            content = render_to_string('predictapp/backtest_report_interactive.html', context)
            # path = os.path.join(BASE_DIR, 'predictapp/static/reports/', '{0}数据说-{1}.html'.format(date.today(), index.index_name))
            # os.makedirs('static/reports/{0}'.format(date.today()), exist_ok=True)
            path = 'static/reports/{0}_{1}.html'.format(date.today(), index_key)
            with open(path, 'w') as static_file:
                static_file.write(content)
            return context
        except:
            log.error(traceback.print_exc())
            return None

    def create_report_topn(self, request, queryset):
        context = self._create_report_interactive(request, index_key=None, n=100)
        return render(request, 'predictapp/backtest_report_interactive.html', context)

    def create_report_xq10like(self, request, queryset):
        context = self._create_report_interactive(request, 'XQ-10-LIKE')
        return render(request, 'predictapp/backtest_report_interactive.html', context)

    def create_report_shg50(self, request, queryset):
        context = self._create_report_interactive(request, 'SHG-50', n=50)
        return render(request, 'predictapp/backtest_report_interactive.html', context)

    def create_report_hs300(self, request, queryset):
        context = self._create_report_interactive(request, 'HS-300', n=300)
        return render(request, 'predictapp/backtest_report_interactive.html', context)

    def create_report_dow30(self, request, queryset):
        context = self._create_report_interactive(request, 'DOW-30', n=30)
        return render(request, 'predictapp/backtest_report_interactive.html', context)

    get_stats.short_description = 'Get statistics'
    run_backtest.short_description = 'Run backtest'
    run_backtest_backend_daily.short_description = 'Run backtest daily with celery'
    run_backtest_backend_weekly.short_description = 'Run backtest weekly with celery'
    run_backtest_backend_monthly.short_description = 'Run backtest monthly with celery'
    import_securities.short_description = 'Import all securities'
    create_report.short_description = 'Create report for selected securities'
    create_report_topn_static.short_description = '收益率排名前{0}_static'.format(100)
    create_report_shg50_static.short_description = '上证50_static'
    create_report_hs300_static.short_description = '沪深300_static'
    create_report_dow30_static.short_description = '道琼斯工业平均指数30_static'

    create_report_topn.short_description = '收益率排名前{0}'.format(100)
    create_report_xq10like.short_description = '雪球关注前10'
    create_report_shg50.short_description = '上证50'
    create_report_hs300.short_description = '沪深300'
    create_report_dow30.short_description = '道琼斯工业平均指数30'

class IndexResource(resources.ModelResource):
    class Meta:
        model = Index

class IndexAdmin(ImportExportModelAdmin):
    resource_class = IndexResource
    search_fields = ['tickers']
    actions = ['import_indexes', 'run_backtest_singlethread', 'run_backtest_multithread',
               'run_backtest_backend_daily', 'run_backtest_backend_weekly', 'run_backtest_backend_monthly',
               'create_report_static', 'create_report_interactive', 'scan_zhangting']

    def import_indexes(self, request, queryset):
        log.info('Admin Import indexes')
        import_indexes()

    def run_backtest_singlethread(self, request, queryset):
        log.info(f'Admin run backtest single thread for index')
        for index in queryset:
            # index_tickers = json.loads(index.tickers)
            index_tickers = index.tickers
            print(f'addd-run backtest single thread of index {index.name}: {index_tickers}')
            run_bulk_backtest_singlethread_task.delay(tickers=index_tickers, delete=True)

    def run_backtest_multithread(self, request, queryset):
        log.info(f'Admin run backtest multi thread for index')
        for index in queryset:
            # index_tickers = json.loads(index.tickers)
            index_tickers = index.tickers
            print(f'addd-run backtest multi thread of index {index.name}: {index_tickers}')
            run_bulk_backtest_multithread_task.delay(tickers=index_tickers, delete=True)

    def run_backtest_backend_daily(self, request, queryset):
        log.info(f'Admin run backtest backend daily for index')
        for index in queryset:
            # index_tickers = json.loads(index.tickers)
            index_tickers = index.tickers
            print(f'addd-run backtest daily of index {index.name}: {index_tickers}')
            for ticker in index_tickers:
                get_backtest_task.delay(ticker)

    def run_backtest_backend_weekly(self, request, queryset):
        log.info(f'Admin run backtest backend weekly for index')
        for index in queryset:
            # index_tickers = json.loads(index.tickers)
            index_tickers = index.tickers
            print(f'addd-run backtest weekly of index {index.name}: {index_tickers}')
            for ticker in index_tickers:
                get_backtest_task.delay(ticker, period='W')

    def run_backtest_backend_monthly(self, request, queryset):
        log.info(f'Admin run backtest backend monthly for index')
        for index in queryset:
            # index_tickers = json.loads(index.tickers)
            index_tickers = index.tickers
            print(f'addd-run backtest monthly of index {index.name}: {index_tickers}')
            for ticker in index_tickers:
                get_backtest_task.delay(ticker, period='M')

    def create_report_static(self, request, queryset):
        log.info(f'Admin create static report for index')
        try:
            for index in queryset:
                n = BACKTEST_REPORT_SECURITIES
                # index_tickers = json.loads(index.tickers)
                index_tickers = index.tickers
                if not index_tickers or index_tickers in ('', '[]'):
                    print(f'addd-create_report_static for ALL, {n}')
                    topn, tickers, table = get_top_securities(n)
                else:
                    # n = min(BACKTEST_REPORT_SECURITIES, len(index_tickers))
                    print(f'addd-create_report_static: {index.name}, {index_tickers}')
                    topn, tickers, table = get_top_securities(n, securities=index_tickers)
                results = get_static_chart(request, tickers)

                context = {'index': index.name,
                           'n': len(tickers),
                           'results': results,
                           'backtest_set': BACKTEST_SET,
                           'strategy_rank': BACKTEST_REPORT_STRATEGY_RANK,
                           'tables': (table,),
                          }
                return render(request, 'predictapp/backtest_report_static.html', context)
        except:
            log.error(traceback.print_exc())
            return render(request, '404.html', {'error': 'Failed to create static report'})

    def create_report_interactive(self, request, queryset):
        log.info(f'Admin create interactive report for index')
        try:
            for index in queryset:
                n = BACKTEST_REPORT_SECURITIES
                # index_tickers = json.loads(index.tickers)
                index_tickers = index.tickers
                if not index_tickers or index_tickers in ('', '[]'):
                    print(f'addd-create_report_interactive for ALL, {n}')
                    topn, tickers, _ = get_top_securities(n)
                else:
                    # n = len(index_tickers)
                    print(f'addd-create_report_interactive: {index.name}, {index_tickers}')
                    topn, tickers, _ = get_top_securities(n, securities=index_tickers)
                results = get_interactive_chart(request, tickers)

                context = {'index': index.name,
                       'n': len(tickers),
                       'topn': topn,
                       'results': results,
                       'backtest_set': BACKTEST_SET,
                       'strategy_rank': BACKTEST_REPORT_STRATEGY_RANK,
                       }
                # Save report to html file
                content = render_to_string('predictapp/backtest_report_interactive.html', context)
                path = 'static/reports/{0}_{1}.html'.format(date.today(), index.symbol)
                with open(path, 'w') as static_file:
                    static_file.write(content)
                print(f'addd-create_report_interactive: {context}')
                return render(request, 'predictapp/backtest_report_interactive.html', context)
        except:
            log.error(traceback.print_exc())
            return render(request, '404.html', {'error': 'Failed to create interactive report'})

    def scan_zhangting(self, request, queryset):
        log.info(f'Admin zhangting scan for index')
        for index in queryset:
            index_tickers = index.tickers
            print(f'addd-scan_zhangting of index {index.name}: {index_tickers}')
            zhangting_scanner(tickers=index_tickers)

    import_indexes.short_description = 'Import all indexes'
    run_backtest_singlethread.short_description = 'Run backtest single thread (delete old)'
    run_backtest_multithread.short_description = 'Run backtest multi thread (delete old)'
    run_backtest_backend_daily.short_description = 'Run backtest backend daily'
    run_backtest_backend_weekly.short_description = 'Run backtest backend weekly'
    run_backtest_backend_monthly.short_description = 'Run backtest backend monthly'
    create_report_static.short_description = 'Create static report'
    create_report_interactive.short_description = 'Create interactive report'
    scan_zhangting.short_description = 'Scan ZhangTing stocks'

class BacktestConditionResource(resources.ModelResource):
    class Meta:
        model = BacktestCondition

class BacktestConditionAdmin(ImportExportModelAdmin):
    resource_class = BacktestConditionResource
    search_fields = ['security__ticker', 'end_time', 'start_time']

class BacktestSummaryResource(resources.ModelResource):
    class Meta:
        model = BacktestSummary

class BacktestSummaryAdmin(ImportExportModelAdmin):
    resource_class = BacktestSummaryResource

class BacktestDetailResource(resources.ModelResource):
    class Meta:
        model = BacktestDetail

class BacktestDetailAdmin(ImportExportModelAdmin):
    resource_class = BacktestDetailResource

# Register your models here.
# admin.site.register(User, UserAdmin)
# admin.site.register(Group, UserAdmin)
admin.site.register(Upload, UploadAdmin)
admin.site.register(Strategy, StrategyAdmin)
admin.site.register(Exchange, ExchangeAdmin)
admin.site.register(Index, IndexAdmin)
admin.site.register(Security, SecurityAdmin)
admin.site.register(BacktestCondition, BacktestConditionAdmin)
admin.site.register(BacktestSummary, BacktestSummaryAdmin)
admin.site.register(BacktestDetail, BacktestDetailAdmin)
