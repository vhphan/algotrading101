from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import datetime
import backtrader as bt
from generic import GenericStrategy


class MyStrategy(GenericStrategy):

    def __init__(self, **kwargs):
        super().__init__()

        for k, v in kwargs.items():
            self.__setattr__(k, v)

        add_header = []
        self.params.dev_multiplier = 5
        for i, d in enumerate(self.datas):
            self.order_refs[d._name] = []
            self.indicators[d] = dict()
            self.indicators[d]['bollinger_inner'] = bt.indicators.BollingerBands(devfactor=1)
            self.indicators[d]['bollinger_outer'] = bt.indicators.BollingerBands(devfactor=2)
            self.indicators[d]['bollinger_inner'].plotinfo.plot = True
            self.indicators[d]['bollinger_inner'].plotinfo.subplot = False
            self.indicators[d]['bollinger_outer'].plotinfo.plot = True
            self.indicators[d]['bollinger_outer'].plotinfo.subplot = False
            # bollinger crossovers
            # from outer band into the inner band
            self.indicators[d]['bollinger_outer_bottom_crossover'] = bt.indicators.CrossOver(d,
                                                                                             bt.indicators.BollingerBands(
                                                                                                 devfactor=1).bot)

            self.indicators[d]['stdev'] = bt.indicators.StandardDeviation(period=self.p.window_s)
            self.indicators[d]['stdev'].plotinfo.plot = False

            # self.add_candles_indicators(d)

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

        # current position size
        pos = self.getposition(d).size

        # indicators
        # for k in indicators:
        #     if k.startswith('bollinger'):
        #         print(k)
        #         # setattr(self, k.replace(' ', '_'), indicators[k])
        #         locals()[k.replace(' ', '_')] = indicators[k]
        bollinger_inner = indicators['bollinger_inner']
        bollinger_outer = indicators['bollinger_outer']
        bollinger_outer_bottom_crossover = indicators['bollinger_outer_bottom_crossover']

        # strategy code here
        self.long_signal = (bollinger_outer_bottom_crossover == 1 and d[-1] > bollinger_outer.bot[-1] and d[0] <
                            bollinger_inner.mid[0])

        if not pos:
            if self.long_signal:
                tp = bollinger_inner.mid[0]
                sl = bollinger_outer.bot[0]
                self.long_action(d, dn, indicators, tp, sl)

            # if self.short_signal and not self.only_long:
            #     self.short_action(d, dn, indicators)

    def short_action(self, d, dn, indicators, take_profit_price=None, stop_price=None):
        entry_price = d[0]
        if take_profit_price is None:
            take_profit_price = entry_price - 2 * indicators['stdev'][0] * self.params.dev_multiplier
        if stop_price is None:
            stop_price = entry_price + indicators['stdev'][0] * self.params.dev_multiplier

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

    def long_action(self, d, dn, indicators, take_profit_price=None, stop_price=None):
        entry_price = d[0]
        if stop_price is None:
            stop_price = d[0] - indicators['stdev'][0] * self.params.dev_multiplier
        if take_profit_price is None:
            take_profit_price = d[0] + 2 * indicators['stdev'][0] * self.params.dev_multiplier

        qty = self.size_position(price=entry_price, stop=stop_price, risk=self.params.risk)

        valid_entry = d.datetime.datetime(0) + datetime.timedelta(hours=self.valid_hours)
        valid_limit = valid_stop = datetime.timedelta(1_000_000)
        # entry_stop_delta = abs(entry_price - stop_price)

        self.buy_order[dn] = self.buy_bracket(data=d, limitprice=take_profit_price,
                                              limitargs=dict(valid=valid_limit),
                                              stopprice=stop_price, stopargs=dict(valid=valid_stop),
                                              exectype=bt.Order.Limit, size=qty, price=entry_price,
                                              valid=valid_entry, )

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
