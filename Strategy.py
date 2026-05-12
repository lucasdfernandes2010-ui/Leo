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

class Emacross:
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

    def __init__(self, df, params):
        self.df = df
        self.ema_window = params['ema_window']
        self.tp = params['tp']
        self.sl = params['tp']

    def signal(self):
        df = self.df 
        df['ema50'] = ta.trend.ema_indicator(df['close'], window=self.ema_window)
        df['signal'] = 0
        df.loc[(df['close'] < df['ema50']) & (df['close'].shift(1) > df['ema50'].shift(1)), 'signal'] = -1
        df['tp'] = self.tp
        df['sl'] = self.sl
        return df 

class MeanReversion:#bad strategy
    """
    strategy
    """
    
    def __init__(self, df, params):
        self.df = df
        self.sma_window = params['sma_window']
        self.entry_std = params['entry_std']

    def signal(self):
        df = self.df
        df['sma'] = ta.trend.ema_indicator(df['close'], window=self.sma_window)
        df['std'] = df['close'].rolling(window=14).std()

        df['entry'] = df['sma'] - self.entry_std * df['std']
        df['signal'] = 0
        df.loc[(df['entry'] > df['close']) & (df['close'].shift(1) > df['entry'].shift(1)), 'signal'] = 1
        df['tp'] = (df['sma'] - df['entry']) / 0.0001
        df['sl'] = df['tp']  
        return df


class ThreeGreenCandles:
    """
    Three Green Candles Strategy — Long Only
    Signal: Three consecutive bullish (green) candles
    Exit: Fixed TP/SL, 1:1 RR
    """

    def __init__(self, df, params):
        self.df = df
        self.tp = params['tp']
        self.sl = params['tp']

    def signal(self):
        df = self.df
        df['signal'] = 0

        green = df['close'] > df['open']

        df.loc[
            green &
            green.shift(1) &
            green.shift(2),
            'signal'
        ] = 1

        df['tp'] = self.tp
        df['sl'] = self.sl
        return df


class BullishEngulfing:
    """
    Bullish Engulfing Strategy — Long Only
    Signal: Bullish engulfing candle while price is above VWAP
    Exit: Fixed TP/SL, 1:1 RR
    """

    def __init__(self, df, params):
        self.df = df
        self.tp = params['tp']
        self.sl = params['tp']

    def signal(self):
        df = self.df

        df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()

        prev_bearish = df['close'].shift(1) < df['open'].shift(1)
        curr_bullish = df['close'] > df['open']
        engulfs      = (df['close'] > df['open'].shift(1)) & (df['open'] < df['close'].shift(1))
        above_vwap   = df['close'] > df['vwap']

        df['signal'] = 0
        df.loc[prev_bearish & curr_bullish & engulfs & above_vwap, 'signal'] = 1

        df['tp'] = self.tp
        df['sl'] = self.sl
        return df