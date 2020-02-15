import backtrader as bt
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler


class Slope(bt.Indicator):
    lines = ('slope', )
    params = (('period', 20),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        y = self.data.get(size=self.p.period)
        x = np.array(range(1, self.p.period + 1)).reshape(-1, 1)
        reg = LinearRegression()  # create object for the class
        reg.fit(x, y)
        self.lines.slope[0] = reg.coef_[0]
        # 💩
