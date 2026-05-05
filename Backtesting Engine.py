import MetaTrader5 as mt5
import pandas as pd 
import random
import matplotlib.pyplot as plt
import numpy as np
import Strategy
import matplotlib.cm as cm
from scipy import stats
import time

"""
The name of this project is Leo

Data Class:
    data_from_api()
    data_from_local()

Strategy Class:
    signal()

Backtest Class:
    enter_trade()
    position_sizing()
    monitor_trade()
    exit_trade()
    run()
    total_time()
    total_candles()

Evaluation Class:
    metrics()
    equity_curve()
    metric_for_optimizer()
    hypothesis_test()
    monte_carlo()
    benchmark()

Execute Class:
    run_for_optimizer()
    run_for_user()

Optimizer Class:
    grid_maker()
    new_params()
    index_range()
    run()

"""

class Data:
    """ 
    Gets data from sources
    Returns a df(data) to Strategy Class
    """

    def __init__(self, symbol, timeframe):
        self.symbol = symbol
        self.timeframe = timeframe

    def data_from_api(self, timeframe, start, end):
        """ 
        This gets data from MT5 api 
        You can access data by date
        """
        mt5.initialize()
        rates = mt5.copy_rates_range(self.symbol, timeframe, start, end)
        df = pd.DataFrame(rates)
        mt5.shutdown()

        df = df.dropna()
        df = df.reset_index(drop=True)
        return df

    def data_from_local(self, pct=100, from_start=False):
        """ 
        This gets data from local storage (data is stored in parquet files)
        You can access this data by a % of the total data available in local storage
        for the selected symbol and timeframe
        You can access a % from the start or the end
        """
        path = f"Data/{self.symbol}/{self.symbol}_{self.timeframe}.parquet"
        df = pd.read_parquet(path)
        n = int(len(df) * pct / 100)

        if from_start:
            df = df.head(n)

        else:
            df = df.tail(n)

        df = df.dropna()
        df = df.reset_index(drop=True)
        return df

class Backtest:
    """
    It takes the df with signals given by Strategy class and backtests
    with risk, leverage, capital, spread, and commision that can be modified
    It gives a new df of trades backtested with entry, exit, size, 
    capital(after trade), and candles to Evaluation Class
    """

    def __init__(self, df, capital, risk, leverage, spread, commission, slippage, max_candle, pip, asset):
        self.df = df
        self.capital = capital
        self.risk = risk
        self.leverage = leverage
        self.spread = spread
        self.commission = commission
        self.slippage = slippage
        self.highs    = df['high'].values
        self.pip = pip
        self.lows     = df['low'].values
        self.opens    = df['open'].values
        self.signals  = df['signal'].values
        self.tp     = df['tp'].iloc[0]
        self.sl = df['sl'].iloc[0]
        self.max_candle = max_candle
        self.asset = asset

    def enter_trade(self, i, signal):
        """
        It takes i(the candle u detect a trade opportunity)
        It enters the trade 
        It adds spread and random slippage
        It calculates entry, tp, sl
        """
        if self.asset == 'forex':
            spread = self.spread * self.pip
            slippage = random.uniform(0, self.slippage) * self.pip
            entry = self.opens[i + 1] + spread + slippage

            if signal == 1:
                tp = entry + self.tp * self.pip
                sl = entry - self.sl * self.pip

            else:
                tp = entry - self.tp * self.pip
                sl = entry + self.sl * self.pip
            
            return entry, sl, tp


        elif self.asset == 'equity':
            spread = self.spread 
            slippage = self.opens[i + 1] * self.slippage
            entry = self.opens[i + 1] + spread + slippage

            if signal == 1:  
                tp = entry * ((100 + self.tp) / 100)
                sl = entry * ((100 - self.sl) / 100)

            else:
                tp = entry * ((100 - self.tp) / 100)
                sl = entry * ((100 + self.sl) / 100)
            
            return entry, sl, tp

    def position_sizing(self, entry, sl):
        """
        It takes entry and sl from enter_trade()
        It calculates the lot size
        Max_lots is calculated with risk and leverage
        Lot_size cannot be greater than max_lots
        """
        if self.asset == 'forex':
            sl_pip = abs(entry - sl) / self.pip
            max_lots = (self.capital * self.leverage) / (100_000 * entry)
            lot_size = (self.capital * self.risk * self.leverage) / (sl_pip * 10)
            lot_size = min(max_lots, lot_size)
            return lot_size

        elif self.asset == 'equity':
            max_size = (self.capital * self.leverage) / entry
            size = (self.capital * self.risk * self.leverage) / abs(entry - sl)
            size = min(size, max_size)
            return size

    def monitor_trade(self, i, entry, tp, sl, size, signal):
        """
        It takes entry, tp, sl from enter_trade()
        It takes lot_size from position_sizing()
        It takes i from the for loop in Backtest.run()
        It monitors the trade 
        If high of a candle is greater than tp, it counts it as a win
        If low if a candle is lesser than sl, it counts it as a loss
        If the trade didnt close after max_candle(int) candles, it closes
        It closes all trade with exit_trade()
        """
        for j in range(i + 1, len(self.df)):
            high  = self.highs[j]
            low   = self.lows[j]
            opens = self.opens[j]

            if j - i == self.max_candle:
                return self.exit_trade(entry, opens, size, j, i, signal)

            if signal == 1:

                if high >= tp and low <= sl:
                    return self.exit_trade(entry, low, size, j, i, signal)

                elif low <= sl:
                    return self.exit_trade(entry, low, size, j, i, signal)

                elif high >= tp:
                    return self.exit_trade(entry, high, size, j, i, signal)

            else:

                if low <= tp and high >= sl:
                    return self.exit_trade(entry, high, size, j, i, signal)

                elif high >= sl:
                    return self.exit_trade(entry, high, size, j, i, signal)

                elif low <= tp:
                    return self.exit_trade(entry, low, size, j, i, signal)

    def exit_trade(self, entry, exit_price, size, j, i, signal):
        """
        It takes entry from enter_trade()
        It takes lot_size from position_sizing()
        It takes exit_price, j, i from monitor_trade
        It exits the trade
        Calculates the pnl(subtracts cost) and adds it to capital
        Returns entry, exit, size, pnl, balance, candles to Backtest.run()
        """
        if self.asset == 'forex':
            if signal == 1:
                pnl = (exit_price - entry) * size * 100_000
            else:
                pnl = (entry - exit_price) * size * 100_000

        elif self.asset == 'equity':
            if signal == 1:
                pnl = (exit_price - entry) * size 
            else:
                pnl = (entry - exit_price) * size 

        cost = self.commission * size
        pnl -= cost
        candles = j - i
        self.capital += pnl
        return {
            'entry': entry, 
            'exit': exit_price, 
            'size': size, 
            'pnl': pnl, 
            'balance': self.capital, 
            'candles': candles,  
            'signal': signal
        }

    def run(self):
        """
        It connects enter_trade(), position_sizing(), 
        monitor_trade, exit_trade() so they all work together
        It appends the trade data given by exit_trade() to a new df
        Returns the new df with the trade data
        """
        trades = []
        for i in range(len(self.df) - 1):
            signal = self.signals[i]
            if signal == 1 or signal == -1:
                entry, sl, tp = self.enter_trade(i, signal)
                size = self.position_sizing(entry, sl)
                trade = self.monitor_trade(i, entry, tp, sl, size, signal)
                if trade:
                    trades.append(trade)
        return pd.DataFrame(trades)

    def total_candles(self):
        """
        It returns the total number of candles 
        in the df(given by Strategy class)
        """
        return len(self.df)

    def total_time(self):
        """
        It returns the total time in years 
        in the df(given by Strategy class)
        """
        start = pd.to_datetime(self.df['time'].iloc[0], unit='s')
        end = pd.to_datetime(self.df['time'].iloc[-1], unit='s')
        delta = end - start
        years = round(delta.days / 365, 2)
        return years

class Evaluation:
    """
    It takes the df of trades, total candles, time in years
    from Backtest class and returns metrics and graphs for
    Optimizer class and for the user
    """

    def __init__(self, trades, candles, years):
        self.trades = trades
        self.candles = candles
        self.years = years

    def metrics(self, trade_type='both'):
        """
        trade_type: 'both', 'long', 'short'
        """
        if trade_type == 'long':
            df = self.trades[self.trades['signal'] == 1].reset_index(drop=True)
        elif trade_type == 'short':
            df = self.trades[self.trades['signal'] == -1].reset_index(drop=True)
        else:
            df = self.trades

        total_trades = len(df)
        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] < 0]
        win_rate = len(wins) / total_trades * 100
        total_pnl = df['pnl'].sum()
        avg_win = wins['pnl'].mean()
        avg_loss = losses['pnl'].mean()
        loss_rate = 1 - (win_rate / 100)
        expectancy = (win_rate / 100 * avg_win) + (loss_rate * avg_loss)
        breakeven_wr = abs(avg_loss) / (avg_win + abs(avg_loss)) * 100
        avg_candles = df['candles'].mean()
        trade_frequency = total_trades / self.years
        profitability_ratio = expectancy * trade_frequency

        rolling_peak = df['balance'].cummax()
        drawdown_pct = (rolling_peak - df['balance']) / rolling_peak * 100
        max_drawdown_pct = drawdown_pct.max()
        profit_factor = wins['pnl'].sum() / abs(losses['pnl'].sum())
        df['returns'] = df['pnl'] / (df['balance'] - df['pnl'])
        sharpe = (df['returns'].mean() / df['returns'].std()) * (len(df) ** 0.5)
        max_loss = (losses['pnl'] / (df['balance'] - df['pnl'])).min() * 100
        downside_returns = df['returns'].copy()
        downside_returns[downside_returns > 0] = 0
        downside_std = (((downside_returns ** 2).mean()) ** 0.5)
        sortino = (df['returns'].mean() / downside_std) * (len(df) ** 0.5)
        var_95 = np.percentile(df['pnl'], 5)
        es_95 = df[df['pnl'] <= var_95]['pnl'].mean()

        print(f"\n--- Metrics ({trade_type.upper()}) ---")
        print(f"Total Trades       : {total_trades}")
        print(f"Win Rate           : {win_rate:.2f}%")
        print(f"Total PnL          : {total_pnl:.2f} usd")
        print(f"Avg Win            : {avg_win:.2f} usd")
        print(f"Avg Loss           : {avg_loss:.2f} usd")
        print(f"Expectancy         : ${expectancy:.2f} per trade")
        print(f"Breakeven WR       : {breakeven_wr:.2f}%")
        print(f"Avg Candles        : {avg_candles:.2f}")
        print(f"Trade Frequency    : {trade_frequency:.2f} trades/year")
        print(f"Profitability Ratio: {profitability_ratio:.2f}")
        print(f"Max Drawdown %     : {max_drawdown_pct:.2f}%")
        print(f"Profit Factor      : {profit_factor:.2f}")
        print(f"Sharpe Ratio       : {sharpe:.2f}")
        print(f"Max Loss           : {max_loss:.2f}%")
        print(f"Sortino Ratio      : {sortino:.2f}")
        print(f"VaR 95             : {var_95:.2f} usd")
        print(f"ES 95              : {es_95:.2f} usd")

    def equity_curve(self):
        """
        It returns a graph of equity curve
        (USD vs No. of Trades)
        """
        df = self.trades
        colour = 'green'
        if df['balance'].iloc[0] > df['balance'].iloc[-1]:
            colour = 'red'

        plt.plot(df.index, df['balance'], color=colour, linewidth=1.5)
        plt.title('Equity Curve')
        plt.xlabel('Trade #')
        plt.ylabel('Balance (USD)')
        plt.grid()
        plt.show()

    def monte_carlo(self, simulations):
        """
        Performs monte carlo simulations to 
        get drawdowns and prob of ruin
        """

        pnl = self.trades['pnl'].values
        n = len(pnl)
        initial_balance = self.trades['balance'].iloc[0] - self.trades['pnl'].iloc[0]

        final_balances = []
        max_drawdowns = []
        all_curves = []

        for i in range(simulations):
            resampled = np.random.choice(pnl, size=n, replace=True)
            curve = initial_balance + np.cumsum(resampled)
            all_curves.append(curve)
            final_balances.append(curve[-1])

            peak = np.maximum.accumulate(curve)
            dd = ((peak - curve) / peak).max() * 100
            max_drawdowns.append(dd)

        final_balances = np.array(final_balances)
        max_drawdowns = np.array(max_drawdowns)

        p5  = np.percentile(final_balances, 5)
        p50 = np.percentile(final_balances, 50)
        p95 = np.percentile(final_balances, 95)
        prob_ruin = (final_balances < initial_balance).mean() * 100
        avg_max_dd = max_drawdowns.mean()
        worst_dd = max_drawdowns.max()

        print(f"\n--- Monte Carlo ({simulations} simulations) ---")
        print(f"Initial Balance  : ${initial_balance:,.2f}")
        print(f"Median Final     : ${p50:,.2f}")
        print(f"5th Percentile   : ${p5:,.2f}")
        print(f"95th Percentile  : ${p95:,.2f}")
        print(f"Prob of Ruin     : {prob_ruin:.2f}%")
        print(f"Avg Max Drawdown : {avg_max_dd:.2f}%")
        print(f"Worst Drawdown   : {worst_dd:.2f}%")

    def benchmark(self, risk_free_rate):
        """
        Compares Leo's performance against a risk free rate benchmark
        """
        rf = risk_free_rate  # 4.5% annual risk free rate
        initial_capital = self.trades['balance'].iloc[0] - self.trades['pnl'].iloc[0]
        
        risk_free_return = initial_capital * (rf * self.years)
        leo_return = self.trades['pnl'].sum()
        
        outperformance = leo_return - risk_free_return

        print(f"\n--- Benchmark (Risk Free Rate) ---")
        print(f"Period           : {self.years} years")
        print(f"Risk Free Return : {risk_free_return:.2f} usd")
        print(f"Leo Return       : {leo_return:.2f} usd")
        print(f"Outperformance   : {outperformance:.2f} usd")

    def hypothesis_test(self):
        """
        H0: mean PnL per trade = 0 (no edge)
        H1: mean PnL per trade > 0 (positive edge)
        One sample t-test on trade PnL for mean pnl
        """

        pnl = self.trades['pnl'].values
        n = len(pnl)
        mean = pnl.mean()
        std = pnl.std(ddof=1)
        std_error = std / (n ** 0.5)

        t_stat = mean / std_error
        p_value = 1 - stats.t.cdf(t_stat, df=n-1) 

        print(f"\n--- Hypothesis Test ---")
        print(f"H0              : Mean PnL = 0")
        print(f"H1              : Mean PnL > 0")
        print(f"P-Value         : {p_value:.4f}")

        if p_value < 0.05:
            print(f"Result          : REJECT H0 — edge is statistically significant (p < 0.05)")
        else:
            print(f"Result          : FAIL TO REJECT H0 — no significant edge (p >= 0.05)")

    def metric_for_optimizer(self):
        """
        It gives one metric(profitability ratio) 
        that Optmizer class will optimize
        """
        df = self.trades
    
        total_trades = len(df)
        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] < 0]
        win_rate = len(wins) / total_trades * 100
        total_pnl = df['pnl'].sum()
        avg_win = wins['pnl'].mean()
        avg_loss = losses['pnl'].mean()
        loss_rate = 1 - (win_rate / 100)
        expectancy = (win_rate / 100 * avg_win) + (loss_rate * avg_loss)
        trade_frequency = total_trades / self.years
        profitability_ratio = expectancy * trade_frequency

        return profitability_ratio

class Optimizer:
    """
    It takes params 
    Params is a dict with keys as the parameters
    that need to be optimized

    The values of Params is a list which work like
    [min, max, step] , this allows us to make a grid
    of parameters and check which combination from 
    the grid returns the greatest metric_for_optimizer

    Optmizer works with random search
    """

    def __init__(self, symbol, timeframe, pct, from_start, capital, risk, leverage, spread, commission, slippage, params, max_candle, pip, asset):
        self.params = params
        self.symbol = symbol
        self.timeframe = timeframe
        self.pct = pct
        self.from_start = from_start
        self.capital = capital
        self.risk = risk
        self.leverage = leverage
        self.spread = spread
        self.commission = commission
        self.slippage = slippage
        self.params = params
        self.max_candle = max_candle
        self.pip = pip 
        self.asset = asset

    def grid_maker(self):
        """
        It makes a grid of parameters called final_grid
        """
        ls = list(self.params.keys())
        final_grid = {}
        for i in range(len(ls)):
            grid = []
            mini = self.params[ls[i]][0]
            maxi = self.params[ls[i]][1]
            step = self.params[ls[i]][2]

            if (maxi - mini) % step == 0: 
                grid.append(mini)
                while maxi != mini:
                    mini += step
                    grid.append(mini)
            else:
                print(f'wrong steps for {ls[i]}')

            final_grid[ls[i]] = grid 

        return final_grid

    def new_params(self, grid, indices):
        """
        It takes final_grid from grid_maker()
        and indices from run()
        indices is a dict with keys same as final_grid
        and values(single number) generated in 
        Optimizer.run() by random search

        Strategy class only expects params with values 
        in the form of single number

        So new_params converts the grid and indices
        into params with values in the form of a 
        single number
        """
        params = {}
        for key in grid:
            params[key] = grid[key][indices[key]]
        return params

    def index_range(self, grid):
        """
        It takes final_grid from grid_maker()
        It makes a new dict called ranges
        with keys same as the original params
        Values of ranges is a list of indices
        These indices are the length of values 
        of each parameter from final_grid
        Ranges help random search picking a 
        random index in Optimize.run()
        """
        ranges = {}
        for key in grid:
            ranges[key] = list(range(len(grid[key])))
        return ranges

    def run(self, runs):
        """
        It takes runs(no. of backtests to optimize) by the user
        It connects grid_maker(), index_range(),
        and new_params() to optimize parameters
        It returns best_params and best_score
        """
        final_grid = self.grid_maker()
        ranges = self.index_range(final_grid)

        best_params = None
        best_score = -999999999999

        for i in range(runs):
            indices = {}
            for key in ranges:
                random_index = random.choice(ranges[key])
                indices[key] = random_index

            params = self.new_params(final_grid, indices)
            config = {
            'symbol':     self.symbol,
            'timeframe':  self.timeframe,
            'pct':        self.pct,
            'from_start': self.from_start,
            'capital':    self.capital,
            'risk':       self.risk,
            'leverage':   self.leverage,
            'spread':     self.spread,
            'commission': self.commission,
            'slippage':   self.slippage,
            'params':     params,
            'max_candle': self.max_candle,
            'pip':        self.pip,
            'asset':      self.asset,
            }
            Exec = Execute(config)
            score = Exec.run_for_optimizer()

            if score > best_score:
                best_score = score
                best_params = params

            print(i)

        return best_params, best_score

class Execute:
    """
    It connects Data class , Strategy class
    Backtest class and Evaluation class to 
    run together
    It makes it easier for the optmizer and 
    the user to Backtest
    It takes all the parameters the other 
    classes take
    """

    def __init__(self, config):
        self.symbol = config['symbol']
        self.timeframe = config['timeframe']
        self.pct = config['pct']
        self.from_start = config['from_start']
        self.capital = config['capital']
        self.risk = config['risk']
        self.leverage = config['leverage']
        self.spread = config['spread']
        self.commission = config['commission']
        self.slippage = config['slippage']
        self.params = config['params']
        self.max_candle = config['max_candle']
        self.pip = config['pip']
        self.asset = config['asset']

    def run_for_optimizer(self):
        """
        It Executes for the optmizer and 
        returns metric_for_optimizer()
        """
        feed = Data(self.symbol, self.timeframe)
        df = feed.data_from_local(pct=self.pct, from_start=self.from_start)

        test = Strategy.Emacross(df, self.params)
        results = test.signal()

        backtest = Backtest(results, self.capital, self.risk, self.leverage, self.spread, self.commission, self.slippage, self.max_candle, self.pip, self.asset)
        backtest_results = backtest.run()

        candles = backtest.total_candles()
        years = backtest.total_time()

        Eval = Evaluation(backtest_results, candles, years)
        return Eval.metric_for_optimizer()

    def run_for_user(self):
        """
        It Executes for the user and returns
        simple_metric(), advanced_metric(),
        and equity_curve()
        """
        feed = Data(self.symbol, self.timeframe)
        df = feed.data_from_local(pct=self.pct, from_start=self.from_start)

        test = Strategy.Emacross(df, self.params)
        results = test.signal()

        backtest = Backtest(results, self.capital, self.risk, self.leverage, self.spread, self.commission, self.slippage, self.max_candle, self.pip, self.asset)
        backtest_results = backtest.run()
        candles = backtest.total_candles()
        years = backtest.total_time()
        
        Eval = Evaluation(backtest_results, candles, years)
        #Eval.metrics('both')
        #Eval.metrics('long')
        Eval.metrics('short')
        Eval.equity_curve()
        Eval.benchmark(0.05)
        Eval.hypothesis_test()
        Eval.monte_carlo(100)

    def run(self, runs):
        Opt = Optimizer(self.symbol, self.timeframe, self.pct, self.from_start, self.capital, self.risk, self.leverage, self.spread, self.commission, self.slippage, self.params, self.max_candle, self.pip, self.asset)
        params, score = Opt.run(runs)
        print(params)
        print(score)
        self.pct = 100 - self.pct
        self.from_start = False
        config = {
            'symbol':     self.symbol,
            'timeframe':  self.timeframe,
            'pct':        self.pct,
            'from_start': self.from_start,
            'capital':    self.capital,
            'risk':       self.risk,
            'leverage':   self.leverage,
            'spread':     self.spread,
            'commission': self.commission,
            'slippage':   self.slippage,
            'params':     params,
            'max_candle': self.max_candle,
            'pip':        self.pip,
            'asset':      self.asset,
        }
        Exec = Execute(config)
        score = Exec.run_for_user()

params_strategy = {
    'ema_window':   [25, 50, 5],
}

config = {
    'symbol':     'EURUSD',
    'timeframe':  'M15',
    'pct':        75,
    'from_start': True,
    'capital':    100_000,
    'risk':       0.0025,
    'leverage':   1,
    'spread':     0.5,
    'commission': 7,
    'slippage':   0.5,
    'params':     params_strategy,
    'max_candle': 1000,
    'pip':        0.0001,
    'asset':      'forex',
}
# symbol, timeframe, pct, from_start, capital, risk, leverage, spread, commission, slippage, params, max_candle, pip, asset
Exec = Execute(config)
score = Exec.run(20)