from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

from backtrader import Analyzer
from backtrader.utils import AutoOrderedDict, AutoDict
from backtrader.utils.py3 import MAXINT


# profitPercAbs = trade.history[1].event.order.executed.price / trade.price
# profitPercAbs = 1 - profitPercAbs if trade.history[1].event.order.executed.size > 0 else profitPercAbs - 1

class TradeReturn(Analyzer):

    def create_analysis(self):
        self.returns_close = []
        self.returns_open = []

    def notify_trade(self, trade):
        # sum(x * y for x, y in zip(rate, amount)) / sum(amount)
        if trade.status == trade.Closed:
            history = trade.history
            count = 0
            open_sizes = []
            close_sizes = []
            open_prices = []
            close_prices = []
            for h in history:
                if h.status.status == 1:
                    count += 1
                    open_prices.append(h.event.price)
                    open_sizes.append(h.event.size)
                if h.status.status == 2:
                    close_prices.append(h.event.price)
                    close_sizes.append(h.event.size)
                    avg_open = sum(x * y for x, y in zip(open_prices, open_sizes)) / sum(open_sizes)
                    num = h.event.order.executed.price
                    profit_pc = num / avg_open
                    profit_pc = 1 - profit_pc if h.event.order.executed.size > 0 else profit_pc - 1
                    self.returns_close.append(round(profit_pc, 4))

            if self.strategy.position.size == 0:
                avg_close = sum(x * y for x, y in zip(close_prices, close_sizes)) / sum(close_sizes)
                for open_price in open_prices:
                    profit_pc_open = avg_close / open_price
                    profit_pc_open = 1 - profit_pc_open if h.event.order.executed.size > 0 else profit_pc_open - 1
                    self.returns_open.append(round(profit_pc_open, 4))

        # if last_event.event.

    def get_analysis(self):
        return dict(returns_close=self.returns_close, returns_open=self.returns_open)
