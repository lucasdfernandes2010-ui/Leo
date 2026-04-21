
class Emacross:

    def __init__(self, df):
        self.df = df

    def signal(self):
        df = self.df 

        df['signal'] = ( (df['close'] > df['ema50']) & (df['close'].shift(1) < df['ema50'].shift(1)) & (df['adx'] > 10) & (df['adx'] < 25) )
        return df 

class MeanReversion:
    def __init__(self, df):
        self.df = df

    def signal(self):
        df = self.df

        df['entry'] = df['sma14'] - 2 * df['std']
        df['tp'] = df['sma14'] - (0) * df['std']
        df['sl'] = df['sma14'] - 3 * df['std']

        df['signal'] = ( (df['entry'] > df['close']) & (df['close'].shift(1) < df['entry'].shift(1)))
        return df

