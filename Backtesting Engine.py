import MetaTrader5 as mt5
import pandas as pd 
from datetime import datetime
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

    def __init__(self, df, capital, risk):
        self.df = df
        self.capital = capital
        self.risk = risk

    def run(self):
        trades = []

        for i in range(len(self.df) - 1):#entering the trade
            if self.df['signal'].iloc[i]:
                entry = self.df['open'].iloc[i + 1] 
                tp = self.df['tp'].iloc[i]
                sl = self.df['sl'].iloc[i]

                sl_pip = (entry - sl) / 0.0001#position sizing
                lot_size = self.capital / (100_000 * entry)

                for j in range(i + 1, len(self.df)):#monitoring the trade
                    high = self.df['high'].iloc[j]
                    low = self.df['low'].iloc[j]

                    if high >= tp:
                        pnl = (tp - entry) * lot_size * 100_000
                        self.capital += pnl
                        trades.append({'entry': entry, 'exit': tp, 'size': lot_size, 'pnl': pnl, 'balance': self.capital})
                        break
                    elif low <= sl:
                        pnl = (sl - entry) * lot_size * 100_000
                        self.capital += pnl
                        trades.append({'entry': entry, 'exit': sl, 'size': lot_size, 'pnl': pnl, 'balance': self.capital})
                        break

        return pd.DataFrame(trades)

class Evaluation:
    def __init__(self, trades):
        self.trades = trades

    def run(self):
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
        rolling_peak = df['balance'].cummax()
        drawdown_pct = (rolling_peak - df['balance']) / rolling_peak * 100
        max_drawdown_pct = drawdown_pct.max()
        profit_factor = wins['pnl'].sum() / abs(losses['pnl'].sum())
        df['returns'] = df['pnl'] / (df['balance'] - df['pnl'])
        sharpe = (df['returns'].mean() / df['returns'].std()) * (252 ** 0.5)

        print(f"Total Trades : {total_trades}")
        print(f"Win Rate     : {win_rate:.2f}%")
        print(f"Total PnL    : {total_pnl:.2f} usd")
        print(f"Avg Win      : {avg_win:.2f} usd")
        print(f"Avg Loss     : {avg_loss:.2f} usd")
        print(f"Expectancy      : ${expectancy:.2f} per trade")
        print(f"Breakeven WR    : {breakeven_wr:.2f}%")
        print(f"Max Drawdown %  : {max_drawdown_pct:.2f}%")
        print(f"Profit Factor   : {profit_factor:.2f}")
        print(f"Sharpe Ratio    : {sharpe:.2f}")

feed = Data("EURUSD", "H1")
df = feed.data_from_local(pct=75, from_start=True)

test = Strategy.MeanReversion(df)
results = test.signal()

backtest = Backtest(results, 100_000, 0.01)
backtest_results = backtest.run()

Eval = Evaluation(backtest_results)
Eval.run()

 