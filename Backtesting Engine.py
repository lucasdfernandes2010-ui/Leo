import MetaTrader5 as mt5
import pandas as pd 
import random
import matplotlib.pyplot as plt
import numpy as np
import itertools
import Strategy
import time

class Data:
    
    def __init__(self, symbol, timeframe):
        self.symbol = symbol
        self.timeframe = timeframe

    def data_from_api(self, timeframe, start, end):
        mt5.initialize()
        rates = mt5.copy_rates_range(self.symbol, timeframe, start, end)
        df = pd.DataFrame(rates)
        mt5.shutdown()

        df = df.dropna()
        df = df.reset_index(drop=True)
        return df

    def data_from_local(self, pct=100, from_start=False):

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

    def __init__(self, df, capital, risk, leverage, spread, commission):
        self.df = df
        self.capital = capital
        self.risk = risk
        self.leverage = leverage
        self.spread = spread
        self.commission = commission

    def run(self):
        trades = []
        for i in range(len(self.df) - 1):#entering the trade
            if self.df['signal'].iloc[i]:
                pip = 0.0001
                spread = self.spread * pip
                entry = self.df['open'].iloc[i + 1] + spread
                tp = entry + self.df['tp_pip'].iloc[0] * pip
                sl = entry - self.df['sl_pip'].iloc[0] * pip

                sl_pip = (entry - sl) / pip#position sizing
                max_lots = (self.capital * self.leverage) / (100_000 * entry)
                lot_size_1 = (self.capital * self.risk) / (sl_pip * 10)
                lot_size = min(max_lots, lot_size_1)

                for j in range(i + 1, len(self.df)):#monitoring the trade
                    high = self.df['high'].iloc[j]
                    low = self.df['low'].iloc[j]
                    opens = self.df['open'].iloc[j]

                    if high >= tp:#exiting the trade
                        pnl = (tp - entry) * lot_size * 100_000
                        cost = self.commission * lot_size
                        pnl -= cost
                        candles = j - i 
                        self.capital += pnl
                        trades.append({'entry': entry, 'exit': tp, 'size': lot_size, 'pnl': pnl, 'balance': self.capital, 'candles': candles})
                        break
                    elif low <= sl:
                        pnl = (sl - entry) * lot_size * 100_000
                        cost = self.commission * lot_size
                        pnl -= cost
                        candles = j - i 
                        self.capital += pnl
                        trades.append({'entry': entry, 'exit': sl, 'size': lot_size, 'pnl': pnl, 'balance': self.capital, 'candles': candles})
                        break
                    elif j - i == self.df['max_candle'].iloc[0]:
                        pnl = (opens - entry) * lot_size * 100_000
                        cost = self.commission * lot_size
                        pnl -= cost
                        candles = j - i
                        self.capital += pnl 
                        trades.append({'entry': entry, 'exit': opens, 'size': lot_size, 'pnl': pnl, 'balance': self.capital, 'candles': candles})
                        break

        return pd.DataFrame(trades)

    def total_candles(self):
        return len(self.df)

    def total_time(self):
        start = self.df['time'].iloc[0]
        end = self.df['time'].iloc[-1]
        delta = end - start
        years = round(delta.days / 365, 2)
        return years

class Evaluation:
    def __init__(self, trades, candles, years):
        self.trades = trades
        self.candles = candles
        self.years = years

    def simple_metrics(self):
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

        print(f"Total Trades : {total_trades}")
        print(f"Win Rate     : {win_rate:.2f}%")
        print(f"Total PnL    : {total_pnl:.2f} usd")
        print(f"Avg Win      : {avg_win:.2f} usd")
        print(f"Avg Loss     : {avg_loss:.2f} usd")
        print(f"Expectancy      : ${expectancy:.2f} per trade")
        print(f"Breakeven WR    : {breakeven_wr:.2f}%")
        print(f"Avg Candles     : {avg_candles:.2f}")

    def advanced_metrics(self):
        df = self.trades
        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] < 0]

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

        print(f"Max Drawdown %  : {max_drawdown_pct:.2f}%")
        print(f"Profit Factor   : {profit_factor:.2f}")
        print(f"Sharpe Ratio    : {sharpe:.2f}")
        print(f"Max Loss        : {max_loss:.2f}%")
        print(f"Sortino Ratio   : {sortino:.2f}")

    def equity_curve(self):
        df = self.trades
        plt.figure(figsize=(12, 5))
        plt.plot(df.index, df['balance'], color='green', linewidth=1.5)
        plt.title('Equity Curve')
        plt.xlabel('Trade #')
        plt.ylabel('Balance (USD)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

    def metric_for_optimizer(self):
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

        return expectancy

class Execute:

    def __init__(self, symbol, timeframe, pct, from_start, capital, risk, leverage, spread, commission, params):
        self.symbol = symbol
        self.timeframe = timeframe
        self.pct = pct
        self.from_start = from_start
        self.capital = capital
        self.risk = risk
        self.leverage = leverage
        self.spread = spread
        self.commission = commission
        self.params = params

    def run_for_optimizer(self):
        feed = Data(self.symbol, self.timeframe)
        df = feed.data_from_local(pct=self.pct, from_start=self.from_start)

        test = Strategy.MeanReversion(df, self.params)
        results = test.signal()

        backtest = Backtest(results, self.capital, self.risk, self.leverage, self.spread, self.commission)
        backtest_results = backtest.run()

        if len(backtest_results) == 0:
            return -999

        candles = backtest.total_candles()
        years = backtest.total_time()

        Eval = Evaluation(backtest_results, candles, years)
        return Eval.metric_for_optimizer()

    def run_for_testing(self):
        feed = Data(self.symbol, self.timeframe)
        df = feed.data_from_local(pct=self.pct, from_start=self.from_start)

        test = Strategy.MeanReversion(df, self.params)
        results = test.signal()

        backtest = Backtest(results, self.capital, self.risk, self.leverage, self.spread, self.commission)
        backtest_results = backtest.run()
        candles = backtest.total_candles()
        years = backtest.total_time()
        
        Eval = Evaluation(backtest_results, candles, years)
        Eval.simple_metrics()
        Eval.advanced_metrics()
        Eval.equity_curve()

class Optimizer:

    def __init__(self, params):
        self.params = params

    def grid_maker(self):
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
        params = {}
        for key in grid:
            params[key] = grid[key][indices[key]]
        return params

    def index_range(self, grid):
        ranges = {}
        for key in grid:
            ranges[key] = list(range(len(grid[key])))
        return ranges

    def index(self, grid, ls):
        indices = {}
        i = 0 
        for key in grid:
            indices[key] = ls[i]
            i += 1

        return indices 

    def run(self, runs):
        final_grid = self.grid_maker()
        ranges = self.index_range(final_grid)

        best_params = None
        best_score = -999

        for i in range(runs):
            indices = {}
            for key in ranges:
                random_index = random.choice(ranges[key])
                indices[key] = random_index
            params = self.new_params(final_grid, indices)
            #symbol, timeframe, pct, from_start, capital, risk, leverage, spread, commission, params
            Exec = Execute("EURUSD", "H1", 75, True, 100_000, 0.0025, 1, 1.5, 3.5, params)
            score = Exec.run_for_optimizer()

            if score > best_score:
                best_score = score
                best_params = params

            print(i)

        return best_params, best_score

params = {
    'sma_window':  [10, 30, 5],
    'std_window':  [10, 20, 2],
    'entry_std':   [1, 2.5, 0.5],
    'tp_pip':      [20, 170, 5],
    'sl_pip':      [20, 70, 5],
    'max_candle':  [10, 30, 5],
}

Opt = Optimizer(params)
params, score = Opt.run(100)
print(params)
print(score)

#symbol, timeframe, pct, from_start, capital, risk, leverage, spread, commission, params
Exec = Execute("EURUSD", "H1", 25, False, 100_000, 0.0025, 1, 1.5, 3.5, params)
score = Exec.run_for_testing()