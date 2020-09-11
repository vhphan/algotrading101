import backtrader as bt
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
from backtrader.indicators import MovingAverageBase, ExponentialSmoothing, StandardDeviation, MovAv
from statistics import stdev
from math import fsum, isnan


class Slope(bt.Indicator):
    lines = ('slope',)
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


# class MACD(Indicator):
#     lines = ('macd', 'signal', 'histo',)
#     params = (('period_me1', 12), ('period_me2', 26), ('period_signal', 9),)
#
#     def __init__(self):
#         me1 = EMA(self.data, period=self.p.period_me1)
#         me2 = EMA(self.data, period=self.p.period_me2)
#         self.l.macd = me1 - me2
#         self.l.signal = EMA(self.l.macd, period=self.p.period_signal)
#         self.l.histo = self.l.macd - self.l.signal

class DummyInd(bt.Indicator):
    lines = ('dummyline',)

    params = (('value', 5),)

    def __init__(self):
        self.lines.dummyline = bt.Max(0.0, self.params.value)


class ExponentialMovingAverageVolatilityAdjusted(bt.Indicator):
    alias = ('EMA_VA',)
    lines = ('emava',)
    params = (('period', 20), ('coeff', 1),)
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.addminperiod(self.p.period)

    def next(self):
        std = stdev(self.data.get(size=self.p.period))
        alpha = (2.0 / (1.0 + self.p.period)) * (1 + std * 10)
        alpha1 = 1 - alpha
        # self.lines.emava[0] = fsum(self.data.get(size=self.p.period)) / self.p.period
        if isnan(self.lines.emava[-1]):
            self.lines.emava[0] = self.data[0]
        else:
            self.lines.emava[0] = self.lines.emava[-1] * alpha1 + self.data[0] * alpha

        # self.lines.emava = 1
        # print('debug emava', self.l.emava[-1], alpha1, self.data[0], alpha)
