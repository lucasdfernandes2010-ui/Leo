import MetaTrader5 as mt5
import pandas as pd 
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
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

    def __init__(self, df, capital, risk, leverage):
        self.df = df
        self.capital = capital
        self.risk = risk
        self.leverage = leverage

    def run(self):
        trades = []

        for i in range(len(self.df) - 1):#entering the trade
            if self.df['signal'].iloc[i]:
                entry = self.df['open'].iloc[i + 1] 
                pip = 0.0001
                tp = entry + self.df['tp_pip'].iloc[i] * pip
                sl = entry - self.df['sl_pip'].iloc[i] * pip

                sl_pip = (entry - sl) / pip#position sizing
                max_lots = (self.capital * self.leverage) / (100_000 * entry)
                lot_size_1 = (self.capital * self.risk) / (sl_pip * 10)
                lot_size = min(max_lots, lot_size_1)

                for j in range(i + 1, len(self.df)):#monitoring the trade
                    high = self.df['high'].iloc[j]
                    low = self.df['low'].iloc[j]
                    opens = self.df['open'].iloc[j]

                    if high >= tp:
                        pnl = (tp - entry) * lot_size * 100_000
                        candles = j - i 
                        self.capital += pnl
                        trades.append({'entry': entry, 'exit': tp, 'size': lot_size, 'pnl': pnl, 'balance': self.capital, 'candles': candles})
                        break
                    elif low <= sl:
                        pnl = (sl - entry) * lot_size * 100_000
                        candles = j - i 
                        self.capital += pnl
                        trades.append({'entry': entry, 'exit': sl, 'size': lot_size, 'pnl': pnl, 'balance': self.capital, 'candles': candles})
                        break
                    elif j - i == 20:
                        pnl = (opens - entry) * lot_size * 100_000
                        candles = j - i
                        self.capital += pnl 
                        trades.append({'entry': entry, 'exit': opens, 'size': lot_size, 'pnl': pnl, 'balance': self.capital, 'candles': candles})
                        break

        return pd.DataFrame(trades)

class Evaluation:
    def __init__(self, trades):
        self.trades = trades

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

class Execute:

    def __init__(self, symbol, timeframe, pct, from_start, capital, risk, leverage, params):
        self.symbol = symbol
        self.timeframe = timeframe
        self.pct = pct
        self.from_start = from_start
        self.capital = capital
        self.risk = risk
        self.leverage = leverage
        self.params = params

    def run(self):
        feed = Data(self.symbol, self.timeframe)
        df = feed.data_from_local(pct=self.pct, from_start=self.from_start)

        test = Strategy.MeanReversion(df, self.params)
        results = test.signal()

        backtest = Backtest(results, self.capital, self.risk, self.leverage)
        backtest_results = backtest.run()

        Eval = Evaluation(backtest_results)
        Eval.simple_metrics()
 
params = {
    'sma_window': 14,
    'std_window': 14,
    'entry_std': 2.0,
    'tp_pip': 50,
    'sl_pip': 50
}

Exec = Execute("EURUSD", "H1", 75, True, 100_000, 0.0025, 1, params)
Exec.run()