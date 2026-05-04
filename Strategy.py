import ta
import pandas as pd 

class Emacross:#good strategy

    def __init__(self, df, params):
        self.df = df
        self.ema_window = params['ema_window']
        self.tp = 20
        self.sl = 40

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
    This is a MeanReversion Strategy
    It takes data in the form of df by Data class
    It also takes params(a dict with keys and values in the form of a single number)
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
        """
        It adds a new column(signal) and tp_pip, sl_pip, max_candle to the original df 
        Signal is a column of true and false, true meaning enter the trade in the next open candle
        and false means to do nothing
        """
        df = self.df
        df['sma'] = ta.trend.sma_indicator(df['close'], window=self.sma_window)
        df['std'] = df['close'].rolling(window=self.std_window).std()

        df['entry'] = df['sma'] - self.entry_std * df['std']
        df['signal'] = ( (df['entry'] > df['close']) & (df['close'].shift(1) > df['entry'].shift(1)))
        df['tp_pip'] = self.tp_pip
        df['sl_pip'] = self.sl_pip
        df['max_candle'] = self.max_candle
        return df

