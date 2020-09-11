from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import datetime
import backtrader as bt
from strategies_bt.generic import GenericStrategy
from indicators import custom_indicators


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
            self.indicators[d]['atr'] = bt.indicators.AverageTrueRange(d)
            self.indicators[d]['bollinger inner'] = bt.indicators.BollingerBands(d, devfactor=1)
            self.indicators[d]['bollinger outer'] = bt.indicators.BollingerBands(d, devfactor=2)
            self.indicators[d]['ichimoku'] = bt.indicators.Ichimoku(d)
            self.indicators[d]['stdev'] = bt.indicators.StandardDeviation(d, period=self.p.window_s)
            self.indicators[d]['rsi'] = bt.indicators.RelativeStrengthIndex(d)
            self.indicators[d]['ema_50'] = bt.indicators.EMA(d, period=50)
            self.indicators[d]['ema_20'] = bt.indicators.EMA(d, period=20)
            self.indicators[d]['ema_10'] = bt.indicators.EMA(d, period=10)
            self.indicators[d]['ema_15'] = bt.indicators.EMA(d, period=15)
            self.indicators[d]['emava_15'] = custom_indicators.EMA_VA(d, period=15)

            self.indicators[d]['ema_15'].plotinfo.plot = False
            self.indicators[d]['emava_15'].plotinfo.plot = False
            self.indicators[d]['ema_10'].plotinfo.plot = False
            self.indicators[d]['ema_50'].plotinfo.plot = False
            self.indicators[d]['ema_20'].plotinfo.plot = False
            self.indicators[d]['ichimoku'].plotinfo.plot = False
            self.indicators[d]['stdev'].plotinfo.plot = False
            self.indicators[d]['bollinger inner'].plotinfo.plot = False
            self.indicators[d]['bollinger outer'].plotinfo.plot = False

            self.indicators[d]['bollinger inner'].plotinfo.subplot = False
            self.indicators[d]['bollinger outer'].plotinfo.subplot = False
            self.indicators[d]['stdev'].plotinfo.subplot = False

            self.add_candles_indicators(d, candle_list=['CDLENGULFING',
                                                        'CDLMORNINGSTAR',
                                                        'CDLEVENINGSTAR',
                                                        'CDLHAMMER',
                                                        'CDLSHOOTINGSTAR'])

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

    @property
    def description(self):
        return """
        
        1) Go long only
        2) long_signal = any_bull_candles_pattern and not any_bear_candles_pattern and above_cloud and is_uptrend
            *) above_cloud = above ichimoku cloud
            *) is_uptrend = ema_10 > ema_20 > ema_50
        3) bull candle patterns ENGULFING, MORNINGSTAR, HAMMER
        4) bear candle patterns ENGULTING, EVENINGSTAR, SHOOTINGSTAR
        5) take profit = close price + 6 * (ATR) where ATR = Average True Range
        6) stop loss = close price - 3 * (ATR) where ATR = Average True Range
        7) take profit only if (is_downtrend or rsi > 70) where is_downtrend = ema_10 < ema_20 < ema_50
        8) if price > take profit price, sell 1/2 of position if is_uptrend where is_uptrend = ema_10 > ema_20 > ema_50
        9) if long_signal triggered when in position, buy more and re-adjust take profit and stop loss to new entry price.
        
        """

    def run_strategy(self, d, data_name, indicators):
        atr = indicators['atr']
        engulfing = indicators['CDLENGULFING']
        morning_star = indicators['CDLMORNINGSTAR']
        evening_star = indicators['CDLEVENINGSTAR']
        hammer = indicators['CDLHAMMER']
        shooting_star = indicators['CDLSHOOTINGSTAR']
        ichimoku = indicators['ichimoku']
        rsi = indicators['rsi']
        ema_50 = indicators['ema_50']
        ema_20 = indicators['ema_20']
        ema_10 = indicators['ema_10']
        stdev = indicators['stdev']
        emava_15 = indicators['emava_15']
        above_cloud = d[0] > ichimoku.senkou_span_a[0] and d[0] > ichimoku.senkou_span_b[0]
        below_cloud = d[0] < ichimoku.senkou_span_a[0] and d[0] < ichimoku.senkou_span_b[0]
        cloud_is_green = ichimoku.senkou_span_a[0] > ichimoku.senkou_span_b[0]
        cloud_is_red = ichimoku.senkou_span_a[0] < ichimoku.senkou_span_b[0]

        any_bull_candles_pattern = (engulfing == 100 or morning_star == 100 or hammer == 100)
        any_bear_candles_pattern = (engulfing == -100 or evening_star == -100 or shooting_star == -100)

        is_uptrend = ema_10 > ema_20 > ema_50
        is_downtrend = ema_10 < ema_20 < ema_50

        self.long_signal = any_bull_candles_pattern and not any_bear_candles_pattern and above_cloud and is_uptrend
        self.short_signal = any_bear_candles_pattern and not any_bull_candles_pattern and below_cloud and is_downtrend

        # self.long_signal = (engulfing == 100) and above_cloud
        # self.short_signal = (engulfing == -100) and below_cloud

        # current position size
        pos = self.getposition(d).size

        # orders still pending 💩💩💩💩
        if self.order_refs[data_name]:
            return

        if not pos:  # no position
            if self.long_signal:
                self.long_action(d, data_name, indicators)  # buy

        else:

            if pos > 0:  # currently long

                take_profit = self.take_profit[d]
                if (d[0] >= take_profit and (is_downtrend or rsi > 70)) or d[0] <= self.stop_loss[d]:
                    self.sell_order[data_name] = self.sell(data=d, exectype=bt.Order.Market, size=pos)
                    self.order_refs[data_name] = [self.sell_order[data_name].ref]
                    self.stop_loss[d] = None
                    self.take_profit[d] = None

                elif self.long_signal:
                    self.long_action(d, data_name, indicators)  # buy more

                elif d[0] >= take_profit and is_uptrend:
                    # sell half and readjust stop loss and take profit
                    self.sell_order[data_name] = self.sell(data=d, exectype=bt.Order.Market, size=pos // 2)
                    self.order_refs[data_name] = [self.sell_order[data_name].ref]
                    self.stop_loss[d] = d[0] - 3 * atr
                    self.take_profit[d] = d[0] + 6 * atr

    @staticmethod
    def rsi_region(rsi):

        if 0 < rsi <= 30:
            return -2
        if 30 < rsi <= 50:
            return -1
        if 50 < rsi <= 70:
            return 1
        if 70 < rsi <= 100:
            return 2

        return None

    def short_action(self, d, dn, indicators):
        return

    def long_action(self, d, dn, indicators):
        self.entry_price[d] = d[0]
        self.stop_loss[d] = d[0] - 3 * indicators['atr'][0]
        self.take_profit[d] = d[0] + 6 * indicators['atr'][0]

        qty = self.size_position(price=self.entry_price[d], stop=self.stop_loss[d], risk=self.params.risk)

        self.buy_order[dn] = self.buy(data=d, exectype=bt.Order.Market, size=qty)
        # self.buy_order[dn] = self.buy_bracket(data=d,
        #                                       limitprice=self.take_profit[d],
        #                                       stopprice=self.stop_loss[d],
        #                                       exectype=bt.Order.Market)

        # self.order_refs[dn] = [o.ref for o in self.buy_order[dn]]
        if self.buy_order[dn] is not None:
            self.order_refs[dn] = [self.buy_order[dn].ref]
        # self.log('BUY CREATE, %.2f' % d.close[0])
        # self.log(f'BUY QUANTITY = {qty}')
        # self.log(f'ENTRY PRICE = {self.entry_price[d]}')
        # self.log(f'SL PRICE = {self.stop_loss[d]}')
        # self.log(f'TP PRICE = {self.take_profit[d]}')
        # self.log(f'CURRENT PRICE = {d[0]}')
