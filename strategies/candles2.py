from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import datetime
import backtrader as bt
from generic import GenericStrategy
from indicators import slope


class MyStrategy(GenericStrategy):

    def __init__(self, **kwargs):
        super().__init__()
        self.taken_first_profit = dict()

        for k, v in kwargs.items():
            self.__setattr__(k, v)

        add_header = []
        self.params.dev_multiplier = 3

        for i, d in enumerate(self.datas):
            self.order_refs[d._name] = []

            self.stop_loss[d] = None
            self.take_profit[d] = None
            self.taken_first_profit[d] = None

            self.indicators[d] = dict()
            self.indicators[d]['bollinger inner'] = bt.indicators.BollingerBands(devfactor=1)
            self.indicators[d]['bollinger outer'] = bt.indicators.BollingerBands(devfactor=2)
            self.indicators[d]['ichimoku'] = bt.indicators.Ichimoku()
            self.indicators[d]['stdev'] = bt.indicators.StandardDeviation(period=self.p.window_s)
            self.indicators[d]['slope'] = slope.Slope(period=self.p.window_l)
            self.indicators[d]['rsi'] = bt.indicators.RelativeStrengthIndex()

            self.indicators[d]['ichimoku'].plotinfo.plot = False
            self.indicators[d]['stdev'].plotinfo.plot = False
            self.indicators[d]['bollinger inner'].plotinfo.plot = False
            self.indicators[d]['bollinger inner'].plotinfo.subplot = False
            self.indicators[d]['bollinger outer'].plotinfo.plot = False
            self.indicators[d]['bollinger outer'].plotinfo.subplot = False

            self.add_candles_indicators(d, candle_list=['CDLENGULFING', 'CDLMORNINGSTAR', 'CDLEVENINGSTAR', 'CDLHAMMER', 'CDLSHOOTINGSTAR'])

            if i == 0:
                for key in self.indicators[d]:
                    add_header.append(key)

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

    def run_strategy(self, d, dn, indicators):

        engulfing = indicators['CDLENGULFING']
        morning_star = indicators['CDLMORNINGSTAR']
        evening_star = indicators['CDLEVENINGSTAR']
        hammer = indicators['CDLHAMMER']
        shooting_star = indicators['CDLSHOOTINGSTAR']
        ichimoku = indicators['ichimoku']
        slope = indicators['slope']
        rsi = indicators['rsi']

        above_cloud = d[0] > ichimoku.senkou_span_a[0] and d[0] > ichimoku.senkou_span_b[0]
        below_cloud = d[0] < ichimoku.senkou_span_a[0] and d[0] < ichimoku.senkou_span_b[0]

        any_bull_candles_pattern = (engulfing == 100 or morning_star == 100 or hammer == 100)
        any_bear_candles_pattern = (engulfing == -100 or evening_star == -100 or shooting_star == -100)

        self.long_signal = any_bull_candles_pattern and not any_bear_candles_pattern and above_cloud
        self.short_signal = any_bear_candles_pattern and not any_bull_candles_pattern and below_cloud

        # self.long_signal = (engulfing == 100) and above_cloud
        # self.short_signal = (engulfing == -100) and below_cloud

        # current position size
        pos = self.getposition(d).size
        if not pos:

            if self.long_signal:
                self.long_action(d, dn, indicators)

            # if self.short_signal and not self.only_long:
            #     self.short_action(d, dn, indicators)
        else:
            if pos > 0:  # currently long

                # strategy 1
                if d[0] >= self.take_profit[d] or d[0] <= self.stop_loss[d]:
                    self.close(d)
                    self.stop_loss[d] = None
                    self.take_profit[d] = None
                else:
                    pass
                    # stop_loss_new = d[0] - indicators['stdev'][0] * self.params.dev_multiplier
                    # self.stop_loss[d] = max(self.stop_loss[d], stop_loss_new)

                # strategy 2
                # if d[0] >= self.take_profit[d] and slope > 0:
                #     self.close(d, size=pos // 2)
                #     self.take_profit[d] = d[0] + 2 * indicators['stdev'][0] * self.params.dev_multiplier
                #
                # elif d[0] >= self.take_profit[d] or d[0] <= self.stop_loss[d]:
                #     self.close(d)
                #     self.stop_loss[d] = None
                #     self.take_profit[d] = None
                #
                # else:
                #     if slope > 0:
                #         stop_loss_new = d[0] - indicators['stdev'][0] * self.params.dev_multiplier
                #         self.stop_loss[d] = max(self.stop_loss[d], stop_loss_new)

    def is_uptrend(self, d, dn, indicators):
        pass

    def short_action(self, d, dn, indicators):
        self.entry_price[d] = d[0]
        self.stop_loss[d] = d[0] + indicators['stdev'][0] * self.params.dev_multiplier
        self.take_profit[d] = d[0] - 2 * indicators['stdev'][0] * self.params.dev_multiplier

        qty = self.size_position(price=self.entry_price[d], stop=self.stop_loss[d], risk=self.params.risk)

        self.sell_order[dn] = self.sell(data=d, exectype=bt.Order.Market, size=qty)
        # self.order_refs[dn] = [o.ref for o in self.buy_order[dn]]
        self.order_refs[dn] = [self.buy_order[dn].ref]
        self.log('BUY CREATE, %.2f' % d.close[0])
        self.log(f'BUY QUANTITY = {qty}')
        self.log(f'ENTRY PRICE = {self.entry_price[d]}')
        self.log(f'SL PRICE = {self.stop_loss[d]}')
        self.log(f'TP PRICE = {self.take_profit[d]}')
        self.log(f'CURRENT PRICE = {d[0]}')

    def long_action(self, d, dn, indicators):
        self.entry_price[d] = d[0]
        self.stop_loss[d] = d[0] - indicators['stdev'][0] * self.params.dev_multiplier
        self.take_profit[d] = d[0] + 2 * indicators['stdev'][0] * self.params.dev_multiplier

        qty = self.size_position(price=self.entry_price[d], stop=self.stop_loss[d], risk=self.params.risk)

        self.buy_order[dn] = self.buy(data=d, exectype=bt.Order.Market, size=qty)
        # self.order_refs[dn] = [o.ref for o in self.buy_order[dn]]
        self.order_refs[dn] = [self.buy_order[dn].ref]
        self.log('BUY CREATE, %.2f' % d.close[0])
        self.log(f'BUY QUANTITY = {qty}')
        self.log(f'ENTRY PRICE = {self.entry_price[d]}')
        self.log(f'SL PRICE = {self.stop_loss[d]}')
        self.log(f'TP PRICE = {self.take_profit[d]}')
        self.log(f'CURRENT PRICE = {d[0]}')
