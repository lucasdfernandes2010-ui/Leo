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
    Exit: Defined TP/SL 
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
        self.std_window = params['std_window']
        self.entry_std = params['entry_std']
        self.tp_pip = params['tp_pip']
        self.sl_pip = params['sl_pip']
        self.max_candle = params['max_candle']

    def signal(self):
        df = self.df
        df['sma'] = ta.trend.sma_indicator(df['close'], window=self.sma_window)
        df['std'] = df['close'].rolling(window=self.std_window).std()

        df['entry'] = df['sma'] - self.entry_std * df['std']
        df['signal'] = ( (df['entry'] > df['close']) & (df['close'].shift(1) > df['entry'].shift(1)))
        df['tp_pip'] = self.tp_pip
        df['sl_pip'] = self.sl_pip
        df['max_candle'] = self.max_candle
        return df
