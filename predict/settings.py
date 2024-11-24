# Windows - xiaomi
# SOURCE_DIR = r'D:\jing\trading_analysis\source'
# PROCESSED_DIR = r'D:\jing\trading_analysis\processed'

# #Ubuntu
# SOURCE_DIR = r'/home/julia/trading_analysis/data/source/'
# PROCESSED_DIR = r'/home/julia/trading_analysis/data/processed/'


SOURCE_COLUMNS = ['date', 'open', 'close', 'high', 'low']
PRICE_COLUMNS = ['low', 'open', 'close', 'high'] # For Google Candlestick Chart
BACKTEST_INPUT_COLUMNS = ['open', 'close', 'high', 'low', 'entry_price', 'up_high_mean', 'up_low_mean', 'down_high_mean', 'down_low_mean', 'position']
BACKTEST_OUTPUT_COLUMNS = ['strategy', 'commission', 'profit_factor', 'loss_factor', 'total_return', 'return_rate',
                           'sharpe', 'drawdown', 'volatility', 'predict_signal', 'limit_price', 'predict_take_profit', 'predict_stop_loss']

# Show strategies with last PUBLIC_STRATEGY_RANK return if user has not paid
PUBLIC_STRATEGY_RANK = 10
# Show strategies with top _PRIVATE_STRATEGY_RANK return if user has paid
PRIVATE_STRATEGY_RANK = 20
# The number of days used to calculate the return, and run the backtest
BACKTEST_SET = 60
# The number of days to get historical data from feed
FEED_DAYS = 120


# Max threads to run bulk backtest
MAX_THREADS = 6
# Max tickers to backtest
MAX_TICKERS = 3000

SHOW_COLUMNS = ['strategy',
                # 'commission', 'profit_factor', 'loss_factor',
                'total_return', 'return_rate',
                # 'sharpe', 'drawdown', 'volatility',
                'predict_signal', 'limit_price', 'predict_take_profit', 'predict_stop_loss']
SHOW_COLUMNS_CN = ['策略', '总收益', '收益率',
                # 'commission', 'profit_factor', 'loss_factor',
                # f'总收益({BACKTEST_SET}天)',
                # 'sharpe', 'drawdown', 'volatility',
                '预测信号', '挂单价', '预测止盈位', '预测止损位']