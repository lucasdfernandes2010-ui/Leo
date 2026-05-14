import ta
import pandas as pd 

""" Each strategy has its own class
    The strategy takes data from
    Data class and adds a column of 
    signal in the form of [-1, 0, 1]
    -1 --> short
    0 ---> do nothing
    1 ---> long
    It also gives columns of tp and sl
    with signal which are added to the
    dataframe given by Data class

    This modified df is given to 
    Backtest class"""

class Emacross1:
    """
    EMA Crossover Strategy — Short Only
    Signal: Price crosses below EMA from above (bearish crossover)
    Exit: Defined TP/SL , 1:1 RR

    {'ema_window': 50, 'tp': 15}
    29939.11081810648
    --- Metrics ---
    Total Trades       : 624
    Win Rate           : 55.93%
    Total PnL          : 8204.18 usd
    Avg Win            : 154.22 usd
    Avg Loss           : -165.89 usd
    Expectancy         : $13.15 per trade
    Breakeven WR       : 51.82%
    Avg Candles        : 15.96
    Trade Frequency    : 1075.86 trades/year
    Profitability Ratio: 14145.13
    Max Drawdown %     : 3.64%
    Profit Factor      : 1.18
    Sharpe Ratio       : 0.06
    Max Loss           : -3.52%
    Sortino Ratio      : 0.09
    VaR 95             : -186.98 usd
    ES 95              : -268.04 usd

    --- Benchmark (Risk Free Rate) ---
    Period           : 0.58 years
    Risk Free Return : 2870.25 usd
    Leo Return       : 8204.18 usd
    Outperformance   : 5333.93 usd

    --- Hypothesis Test ---
    H0              : Mean PnL = 0
    H1              : Mean PnL > 0
    P-Value         : 0.0243
    Result          : REJECT H0 — edge is statistically significant (p < 0.05)

    --- Monte Carlo (100 simulations) ---
    Initial Balance  : $100,000.00
    Median Final Bal    : $108,432.55
    5th Percentile Bal   : $101,132.52
    95th Percentile Bal  : $114,458.72
    Prob of Ruin     : 2.00%
    Median MaxDD : 2.54%
    5th Percentile MaxDD   : 1.52%
    95th Percentile MaxDD  : 4.71%
    [Finished in 72.4s]
    """

    def __init__(self, df):
        self.df = df

    def indicator(self):
        df = self.df

        return df

    def signal(self, params):
        self.ema_window = params['ema_window']
        self.tp = params['tp']
        self.sl = params['tp']

        df = self.df 
        df['ema50'] = ta.trend.ema_indicator(df['close'], window=self.ema_window)
        df['signal'] = 0
        df.loc[(df['close'] < df['ema50']) & (df['close'].shift(1) > df['ema50'].shift(1)), 'signal'] = -1
        df['tp'] = self.tp
        df['sl'] = self.sl
        return df 

class Emacross2:
    """
    EMA Crossover Strategy — Short Only

    Signal : Price crosses below EMA + MFI between mfi1 and mfi2
    Exit   : TP/SL 1:1 RR, MFI window fixed at 14

    Params : ema_window, mfi1, mfi2, tp
    """

    def __init__(self, df):
        self.df = df
        self.mfi_window = 14

    def indicator(self):#indicators which do not change with params 
        df = self.df
        df['mfi'] = ta.volume.money_flow_index(df['high'], df['low'], df['close'], df['volume'], window=self.mfi_window)

        return df

    def signal(self, params):#indicators that do change with params
        self.ema_window = params['ema_window']
        self.mfi1 = 0
        self.mfi2 = 100
        self.tp = params['tp']
        self.sl = params['tp'] 

        df = self.df
        df['ema'] = ta.trend.ema_indicator(df['close'], window=self.ema_window)
        df['signal'] = 0

        ema_cross = (df['close'] > df['ema']) & (df['close'].shift(1) < df['ema'].shift(1))
        mfi_filter = (df['mfi'] >= self.mfi1) & (df['mfi'] <= self.mfi2)

        df.loc[ema_cross & mfi_filter, 'signal'] = 1

        df['tp'] = self.tp
        df['sl'] = self.sl
        return df