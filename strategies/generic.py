from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime

import backtrader as bt


class GenericStrategy(bt.Strategy):
    params = dict(window_s=21, window_m=50, window_l=100, window_xs=5, risk=0.01, stop_dist=0.05, dev_multiplier=2)

    def __init__(self):
        # custom parameter
        timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d%H%M%S')
        cn = self.__class__.__module__

        self.csv_file = f'output/{cn}-{timestamp}-bt-run.csv'
        self.csv_file_orders = f'output/{cn}-{timestamp}-bt-orders.csv'

        # To keep track of pending orders and buy price/commission
        self.order_refs = dict()
        self.buy_order = dict()
        self.sell_order = dict()
        self.indicators = dict()
        self.long_signal = False
        self.short_signal = False

    def next(self):

        for i, d in enumerate(self.datas):

            dt, dn = self.datetime.datetime(0), d._name
            pos = self.getposition(d).size
            indicators = self.indicators[d]

            with open(self.csv_file, 'a+') as f:
                df_log = f'{dn}, {dt}, {d.open[0]}, {d.high[0]}, {d.low[0]}, {d.close[0]}, {d.volume[0]}, {self.long_signal}, {self.short_signal}'
                for key in indicators:
                    df_log += f', {round(indicators[key][0], 5)}'

                f.write(df_log + '\n')

            # if pos > 0:
            #     print('{} {} Position {}'.format(dt, dn, pos))

            # self.log(
            #     f'{dn} Open, {d.open[0]:.4f}, High, {d.high[0]:.4f}, Low, {d.low[0]:.4f}, Close, {d.close[0]:.4f}')

            cash = self.broker.get_cash()
            # Check if an order is pending ... if yes, we cannot send a 2nd one

            if self.order_refs[dn]:
                return
            # else:
            #     print(f'no order refs for {dn}')

            self.run_strategy(d, dn, indicators)

    def run_strategy(self, d, dn, indicators):
        print(f'running strategy {self.__name__}')
        self.long_signal = False
        self.short_signal = False

    def short_action(self, d, dn, indicators):
        pass

    def long_action(self, d, dn, indicators):
        pass

    def log(self, txt, dt=None):
        """ Logging function fot this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        dt1 = self.data0.datetime.time(0)

        # print('%s, %s' % (dt.isoformat(), txt))
        print('%s,%s, %s' % (dt.isoformat(), dt1.isoformat(), txt))

    def setup_csv_files(self, add_header=None):
        """
        Function to setup csv file to log the strategy execution.
        The file can then be analyzed with pandas later.
        """

        if add_header is None:
            add_header = []
        basic_header = ['instrument', 'datetime', 'open', 'high', 'low', 'close', 'volume', 'long_signal',
                        'short_signal']
        # Write the header to the trade log.
        header = basic_header + add_header

        with open(self.csv_file, 'w') as file:
            file.write(','.join(header) + "\n")

        header_order = ['instrument', 'datetime', 'buy/sell', 'status', 'size', 'order ref']
        with open(self.csv_file_orders, 'w') as file:
            file.write(','.join(header_order) + "\n")

    def notify_order(self, order):

        buy_or_sell = 'Buy' * order.isbuy() or 'Sell'

        dt, dn = self.datetime.datetime(0), order.data._name
        print('{} {} Order {} {} Status {}'.format(
            dt, dn, order.ref, buy_or_sell, order.getstatusname())
        )

        with open(self.csv_file_orders, 'a+') as f:
            log_order = f'{dn}, {dt}, {buy_or_sell}, {order.getstatusname()}, {order.size}, {order.ref}'
            f.write(log_order + '\n')

        if not order.alive():
            for i, d in enumerate(self.datas):
                if order.ref in self.order_refs[d._name]:
                    self.order_refs[d._name].remove(order.ref)

        print('{}: Order ref: {} / Type {} / Status {} / Instrument {}'.format(
            self.data.datetime.datetime(0),
            order.ref, 'Buy' * order.isbuy() or 'Sell',
            order.getstatusname(),
            self.data._name))

        if order.status == order.Completed:
            print(f'order completed, executed price = {order.executed.price}')

    def notify_trade(self, trade):
        date = self.data.datetime.datetime()
        if trade.isclosed:
            print('-' * 32, ' NOTIFY TRADE ', '-' * 32)
            print('{}, Entry Price: {}, Profit, Gross {}, Net {}'.format(
                date,
                trade.price,
                round(trade.pnl, 2),
                round(trade.pnlcomm, 2)))
            print('-' * 80)

    def stop(self):
        print('stopping')
        # result = list()
        # result.append(pd.DataFrame({'kijun_sen': self.ichimoku.kijun_sen.get(size=len(self.ichimoku))}))
        # result.append(pd.DataFrame({'tenkan_sen': self.ichimoku.tenkan_sen.get(size=len(self.ichimoku))}))
        # result_df = pd.concat(result, axis=1)

        # for item in self.indobscsv:
        #     print(type(item))
        #     print(getattr(item, '__module__', None))

    # from https://backtest-rookies.com/2017/06/06/code-snippet-forex-position-sizing/
    def size_position(self, price, stop, risk, method=0, exchange_rate=None, jpy_pair=False):
        """
        Helper function to calcuate the position size given a known amount of risk.

        *Args*
        - price: Float, the current price of the instrument
        - stop: Float, price level of the stop loss
        - risk: Float, the amount of the account equity to risk

        *Kwargs*
        - JPY_pair: Bool, whether the instrument being traded is part of a JPY
        pair. The muliplier used for calculations will be changed as a result.
        - Method: Int,
            - 0: Acc currency and counter currency are the same
            - 1: Acc currency is same as base currency
            - 2: Acc currency is neither same as base or counter currency
        - exchange_rate: Float, is the exchange rate between the account currency
        and the counter currency. Required for method 2.

        Return value of units to buy/sell. To convert to lot:
        units/100_000 = # of lots
        units/10_000 = # of mini lots
        units/1_000 = # of micro lots
        """

        if jpy_pair:  # check if a YEN cross and change the multiplier
            multiplier = 0.01
        else:
            multiplier = 0.0001

        # Calc how much to risk
        acc_value = self.broker.getvalue()
        cash_risk = acc_value * risk
        stop_pips_int = abs((price - stop) / multiplier)  # number of pips between price and stop
        pip_value = cash_risk / stop_pips_int

        if method == 1:
            # pip_value = pip_value * price
            units = pip_value / multiplier
            return units

        elif method == 2:
            pip_value = pip_value * exchange_rate
            units = pip_value / multiplier
            return units

        else:  # is method 0
            units = pip_value / multiplier
            return units

    def add_candles_indicators(self, d, candle_list=None):
        if candle_list is None:
            candle_list = ['CDLENGULFING', 'CDLMORNINGSTAR', 'CDLEVENINGSTAR', 'CDLHAMMER', 'CDLSHOOTINGSTAR']
        cdl_methods = [m for m in dir(bt.talib) if 'CDL' in m and m in candle_list]
        for cdl_method in cdl_methods:
            self.indicators[d][cdl_method] = getattr(bt.talib, cdl_method)(d.open, d.high, d.low, d.close)
            self.indicators[d][cdl_method].plotinfo.plot = True
            self.indicators[d][cdl_method].plotinfo.subplot = True
            self.indicators[d][cdl_method].csv = True


