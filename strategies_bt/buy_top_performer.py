from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import datetime
import backtrader as bt
from strategies_bt.generic import GenericStrategy
from indicators import custom_indicators
import pandas as pd


class MyStrategy(GenericStrategy):

    def __init__(self, **kwargs):
        super().__init__()

        for k, v in kwargs.items():
            self.__setattr__(k, v)

        add_header = []

        for i, d in enumerate(self.datas):
            self.order_refs[d._name] = []

            self.stop_loss[d] = None
            self.take_profit[d] = None

            self.indicators[d] = dict()
            self.indicators[d]['atr'] = bt.indicators.AverageTrueRange(d)
            self.indicators[d]['stdev'] = bt.indicators.StandardDeviation(d, period=21)
            self.indicators[d]['ema_50'] = bt.indicators.ExponentialMovingAverage(d, period=50)
            self.indicators[d]['ema_20'] = bt.indicators.ExponentialMovingAverage(d, period=20)
            self.indicators[d]['ema_10'] = bt.indicators.ExponentialMovingAverage(d, period=10)
            self.indicators[d]['ema_15'] = bt.indicators.ExponentialMovingAverage(d, period=15)
            self.indicators[d]['pct_change'] = bt.indicators.PctChange(d, period=48)

            if i == 0:
                for key in self.indicators[d]:
                    add_header.append(key)

        self.top_five = None
        self.setup_csv_files(add_header=add_header)

        current_time_frame = bt.TimeFrame.Names[self.data._timeframe]
        valid_candles = 10
        if current_time_frame == 'Days':
            multiplier = 24 / self.data._compression
        elif current_time_frame == 'Minutes':
            multiplier = self.data._compression / 60
        else:
            multiplier = 10

        self.valid_hours = valid_candles * multiplier

    @property
    def description(self):
        return """

        1) Go long only
        2) 

        """

    def next(self):

        pct_change_list = []
        pos = {}
        for i, d in enumerate(self.datas):
            dt, dn = self.datetime.datetime(0), d._name
            pos[dn] = self.getposition(d).size
            indicators = self.indicators[d]
            pct_change_list.append(dict(symbol=dn, pct_change=indicators['pct_change'][0]))
        df_pct_change = pd.DataFrame(pct_change_list)
        df_pct_change.sort_values(by='pct_change', ascending=False, inplace=True)
        print(df_pct_change.head())

        if self.top_five is None:
            return
        self.top_five = df_pct_change[df_pct_change['pct_change'] > 0.1].head()['symbol'].to_list()



    def run_strategy(self, **kwargs):
        pass

    def short_action(self, d, dn, indicators):
        return

    def long_action(self, d, dn, indicators):

        self.buy_order[dn] = self.buy(data=d, exectype=bt.Order.Market, size=100)

        if self.buy_order[dn] is not None:
            self.order_refs[dn] = [self.buy_order[dn].ref]
