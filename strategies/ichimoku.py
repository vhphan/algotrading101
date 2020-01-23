# from __future__ import (absolute_import, division, print_function,
#                         unicode_literals)
import datetime
import backtrader as bt
from generic import GenericStrategy


class Ichimoku(GenericStrategy):

    def __init__(self):
        super(Ichimoku, self).__init__()
        add_header = []
        self.std_scale = 5
        for i, d in enumerate(self.datas):
            self.order_refs[d._name] = []
            self.indicators[d] = dict()
            self.indicators[d]['ichimoku'] = bt.indicators.Ichimoku()
            self.indicators[d]['stdev'] = bt.indicators.StandardDeviation(period=self.p.window_s)
            self.indicators[d]['ichimoku'].plotinfo.plot = False
            self.indicators[d]['stdev'].plotinfo.plot = False
            self.indicators[d]['bollinger outer'].plotinfo.plot = False
            self.indicators[d]['bollinger outer'].plotinfo.subplot = False

            cdl_methods = [m for m in dir(bt.talib) if 'CDL' in m]
            for cdl_method in cdl_methods:
                self.indicators[d][cdl_method] = getattr(bt.talib, cdl_method)(d.open, d.high, d.low, d.close)
                if cdl_method in ['CDLENGULFING', 'CDLMORNINGSTAR', 'CDLEVENINGSTAR',
                                  'CDLHAMMER', 'CDLSHOOTINGSTAR']:
                    self.indicators[d][cdl_method].plotinfo.plot = True
                    self.indicators[d][cdl_method].plotinfo.subplot = True
                    self.indicators[d][cdl_method].csv = True
                else:
                    self.indicators[d][cdl_method].plotinfo.plot = False
                    self.indicators[d][cdl_method].plotinfo.subplot = False

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

        bollinger_inner_upper = indicators['bollinger inner'].top
        bollinger_inner_lower = indicators['bollinger inner'].bot
        bollinger_outer_upper = indicators['bollinger outer'].top
        bollinger_outer_lower = indicators['bollinger outer'].bot

        sell_zone = bollinger_outer_lower < d[0] < bollinger_inner_lower
        buy_zone = bollinger_inner_upper < d[0] < bollinger_outer_upper

        above_cloud = d[0] > ichimoku.senkou_span_a[0] and d[0] > ichimoku.senkou_span_b[0]
        below_cloud = d[0] < ichimoku.senkou_span_a[0] and d[0] < ichimoku.senkou_span_b[0]

        any_bull_candles_pattern = (engulfing == 100 or morning_star == 100 or hammer == 100)
        any_bear_candles_pattern = (engulfing == -100 or evening_star == -100 or shooting_star == -100)

        self.long_signal = any_bull_candles_pattern and not any_bear_candles_pattern and above_cloud
        self.short_signal = any_bear_candles_pattern and not any_bull_candles_pattern and below_cloud

        # self.long_signal = (engulfing == 100) and above_cloud
        # self.short_signal = (engulfing == -100) and below_cloud

        if self.long_signal:
            self.long_action(d, dn, indicators)

        if self.short_signal:
            self.short_action(d, dn, indicators)

    def short_action(self, d, dn, indicators):
        entry_price = d[0]
        stop_price = entry_price + indicators['stdev'][0] * self.std_scale
        take_profit_price = entry_price - 2 * indicators['stdev'][0] * self.std_scale

        qty = self.size_position(price=entry_price, stop=stop_price, risk=self.params.risk)

        valid_entry = d.datetime.datetime(0) + datetime.timedelta(hours=self.valid_hours)
        valid_limit = valid_stop = datetime.timedelta(1000000)
        # entry_stop_delta = abs(entry_price - stop_price)

        self.sell_order[dn] = self.sell_bracket(data=d, limitprice=take_profit_price,
                                                limitargs=dict(valid=valid_limit),
                                                stopprice=stop_price, stopargs=dict(valid=valid_stop),
                                                exectype=bt.Order.Limit, size=qty, price=entry_price,
                                                valid=valid_entry)

        # self.sell_order[dn] = self.sell_bracket(data=d, limitprice=take_profit_price,
        #                                         limitargs=dict(valid=valid_limit),
        #                                         stopargs=dict(valid=valid_stop),
        #                                         exectype=bt.Order.StopTrail, size=qty, price=entry_price,
        #                                         valid=valid_entry, trailamount=entry_stop_delta)

        self.order_refs[dn] = [o.ref for o in self.sell_order[dn]]
        self.log('SHORT SELL CREATE, %.2f' % d.close[0])
        self.log(f'SELL QUANTITY = {qty}')
        self.log(f'ENTRY PRICE = {entry_price}')
        self.log(f'SL PRICE = {stop_price}')
        self.log(f'TP PRICE = {take_profit_price}')
        self.log(f'CURRENT PRICE = {d[0]}')

    def long_action(self, d, dn, indicators):
        entry_price = d[0]
        stop_price = d[0] - indicators['stdev'][0] * self.std_scale
        take_profit_price = d[0] + 2 * indicators['stdev'][0] * self.std_scale

        qty = self.size_position(price=entry_price, stop=stop_price, risk=self.params.risk)

        valid_entry = d.datetime.datetime(0) + datetime.timedelta(hours=self.valid_hours)
        valid_limit = valid_stop = datetime.timedelta(1_000_000)
        # entry_stop_delta = abs(entry_price - stop_price)

        self.buy_order[dn] = self.buy_bracket(data=d, limitprice=take_profit_price,
                                              limitargs=dict(valid=valid_limit),
                                              stopprice=stop_price, stopargs=dict(valid=valid_stop),
                                              exectype=bt.Order.Limit, size=qty, price=entry_price,
                                              valid=valid_entry,)

        # self.buy_order[dn] = self.buy_bracket(data=d, limitprice=take_profit_price,
        #                                       limitargs=dict(valid=valid_limit),
        #                                       stopargs=dict(valid=valid_stop),
        #                                       exectype=bt.Order.StopTrail, size=qty, price=entry_price,
        #                                       valid=valid_entry, trailamount=entry_stop_delta)

        self.order_refs[dn] = [o.ref for o in self.buy_order[dn]]
        self.log('BUY CREATE, %.2f' % d.close[0])
        self.log(f'BUY QUANTITY = {qty}')
        self.log(f'ENTRY PRICE = {entry_price}')
        self.log(f'SL PRICE = {stop_price}')
        self.log(f'TP PRICE = {take_profit_price}')
        self.log(f'CURRENT PRICE = {d[0]}')
