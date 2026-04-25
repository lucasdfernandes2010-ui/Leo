import ta
import pandas as pd 

class Emacross:

    def __init__(self, df):
        self.df = df

    def signal(self):
        df = self.df 
        df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['sma14'] = ta.trend.sma_indicator(df['close'], window=14)
        df['std14'] = df['close'].rolling(window=14).std()
        df['adx14'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)

        df['signal'] = ( (df['close'] > df['ema50']) & (df['close'].shift(1) < df['ema50'].shift(1)) & (df['adx14'] > 10) & (df['adx14'] < 25) )
        return df 

class MeanReversion:
    def __init__(self, df, params):
        self.df = df
        self.sma_window = params['sma_window']
        self.std_window = params['std_window']
        self.entry_std = params['entry_std']
        self.tp_pip = params['tp_pip']
        self.sl_pip = params['sl_pip']

    def signal(self):
        df = self.df
        df['sma'] = ta.trend.sma_indicator(df['close'], window=self.sma_window)
        df['std'] = df['close'].rolling(window=self.std_window).std()

        df['entry'] = df['sma'] - self.entry_std * df['std']
        df['signal'] = ( (df['entry'] > df['close']) & (df['close'].shift(1) > df['entry'].shift(1)))
        df['tp_pip'] = self.tp_pip
        df['sl_pip'] = self.sl_pip
        return df

