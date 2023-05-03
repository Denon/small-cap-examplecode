# 导入函数库
from jqdata import *

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    
    # 每月第一个交易日进行调仓
    run_monthly(rebalance, 1)

# 调仓策略
def rebalance(context):
    # 获取股票池
    stock_list = get_stock_pool(context)

    # 判断股票是否可交易并且是否涨停
    valid_stocks = []
    for stock in stock_list:
        if not is_st(stock) and not is_new(stock, context) and not is_north(stock) and not is_suspended(stock, context):
            if not is_high_limit(context, [stock])[stock]:
                valid_stocks.append(stock)

    # 对剩余股票按流通市值从小到大排序，并选出前100只
    smallest_market_cap_stocks = get_smallest_market_cap(valid_stocks, 100)

    # 计算每只股票的目标持仓比例
    target_weight = 1.0 / len(smallest_market_cap_stocks)

    # 平仓不在股票池中的股票
    for stock in context.portfolio.positions.keys():
        if stock not in smallest_market_cap_stocks:
            order_target(stock, 0)

    # 调整股票仓位
    for stock in smallest_market_cap_stocks:
        current_weight = context.portfolio.positions[stock].value / context.portfolio.total_value
        target_value = context.portfolio.total_value * target_weight
        if current_weight != target_weight:
            order_target_value(stock, target_value)

# 获取剔除ST、*ST、北交所、上市不满20日次新股的股票池
def get_stock_pool(context):
    stock_list = list(get_all_securities(['stock']).index)
    q = query(valuation).filter(valuation.code.in_(stock_list)).order_by(valuation.circulating_market_cap.asc()).limit(300)
    df = get_fundamentals(q)
    return list(df['code'])


# 获取流通市值最小的n只股票
def get_smallest_market_cap(stock_list, n):
    market_caps = {}
    q = query(valuation).filter(valuation.code.in_(stock_list)).order_by(valuation.circulating_market_cap.asc()).limit(100)
    df = get_fundamentals(q)
    return list(df['code'])

# 判断是否为ST或*ST股票
def is_st(stock):
    stock_info = get_security_info(stock)
    return stock_info.display_name.startswith('ST') or stock_info.display_name.startswith('*ST')

# 判断是否为上市不满20日次新股
def is_new(stock, context):
    current_date = context.current_dt.date()
    days_public = (current_date - get_security_info(stock).start_date).days
    return days_public < 20

# 判断是否为北交所股票
def is_north(stock):
    return stock.startswith('N')

# 判断是否为停牌股票
def is_suspended(stock, context):
    today = context.current_dt.strftime('%Y-%m-%d')
    stock_data = get_price(stock, end_date=today, count=1, fields=['paused'])
    return stock_data.iloc[-1]['paused'] == 1


# 获取指定股票的估值数据
def get_valuation(stock, field):
    fundamentals_df = get_fundamentals(query(valuation).filter(valuation.code == stock))
    if not fundamentals_df.empty:
        return fundamentals_df.iloc[0][field]
    else:
        return None


def is_high_limit(context, stock_list):
    end_date = context.current_dt
    start_date = end_date - timedelta(days=1)
    price_data = get_price(stock_list, start_date=start_date, end_date=end_date, fields=['close', 'high_limit'], panel=False)
    
    result = {}
    for stock in stock_list:
        if stock in price_data.index:
            result[stock] = price_data.loc[stock]['close'] >= price_data.loc[stock]['high_limit']
        else:
            result[stock] = False
            
    return result

def is_trading(context, stock_list):
    end_date = context.current_dt
    start_date = end_date - timedelta(days=1)
    price_data = get_price(stock_list, start_date=start_date, end_date=end_date, fields=['paused'], panel=False)
    
    result = {}
    for stock in stock_list:
        if stock in price_data.index:
            result[stock] = not price_data.loc[stock]['paused']
        else:
            result[stock] = False
            
    return result

