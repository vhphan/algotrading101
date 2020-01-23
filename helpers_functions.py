from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import csv
import math
import os

import backtrader as bt
import pandas as pd


def my_position_size(cash, stop_price, entry_price, risk):
    # qty_max = math.floor((0.9 * cash) / close_price)
    # abs (stopprice/entry price)-1

    qty_1 = math.floor((cash * risk) / abs(1 - stop_price / entry_price))
    max_qty = math.floor(0.5 * cash / entry_price)
    qty = min(max_qty, qty_1)

    print('cash =', cash)
    print('risk =', risk)
    print('stop price =', stop_price)
    print('entry price =', entry_price)
    print('intial size =', qty_1)
    print('price =', entry_price)
    print('cost =', qty_1 * entry_price)
    print('final size =', qty)

    return qty


def save_trade_analysis(analyzer, instrument, csv_file):
    results = dict(
        instrument=instrument,
        total_open=analyzer.total.open,
        total_closed=analyzer.total.closed,
        total_won=analyzer.won.total,
        total_lost=analyzer.lost.total,
        win_streak=analyzer.streak.won.longest,
        lose_streak=analyzer.streak.lost.longest,
        pnl_net=round(analyzer.pnl.net.total, 2),
        strike_rate=round(analyzer.won.total / analyzer.total.closed, 3))
    csv_columns = results.keys()

    file_exists = os.path.isfile(csv_file)
    try:
        with open(csv_file, 'a', newline='') as csv_file:

            writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
            if not file_exists:
                writer.writeheader()
            writer.writerow(results)

    except IOError:
        print("I/O error")


def print_trade_analysis(analyzer):
    '''
    Function to print the Technical Analysis results in a nice format.
    '''
    # Get the results we are interested in
    total_open = analyzer.total.open
    total_closed = analyzer.total.closed
    total_won = analyzer.won.total
    total_lost = analyzer.lost.total
    win_streak = analyzer.streak.won.longest
    lose_streak = analyzer.streak.lost.longest
    pnl_net = round(analyzer.pnl.net.total, 2)
    strike_rate = round((total_won / total_closed) * 100, 3)
    # Designate the rows
    h1 = ['Total Open', 'Total Closed', 'Total Won', 'Total Lost']
    h2 = ['Strike Rate', 'Win Streak', 'Losing Streak', 'PnL Net']
    r1 = [total_open, total_closed, total_won, total_lost]
    r2 = [strike_rate, win_streak, lose_streak, pnl_net]
    # Check which set of headers is the longest.
    if len(h1) > len(h2):
        header_length = len(h1)
    else:
        header_length = len(h2)
    # Print the rows
    print_list = [h1, r1, h2, r2]
    row_format = "{:<15}" * (header_length + 1)
    print("Trade Analysis Results:")
    for row in print_list:
        print(row_format.format('', *row))


def print_sqn(analyzer):
    sqn = round(analyzer.sqn, 2)
    print('SQN: {}'.format(sqn))


def print_sharpe_ratio(analyzer):
    sharpe = analyzer['sharperatio']
    print(f'Sharpe Ratio: {sharpe}')


def print_generic_analysis(analyzer):
    for k, v in analyzer.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                print(f"{k2} = {v2:.2f}")
        else:
            print(f"{k} = {v:.2f}")


def print_dict(d, depth=0):
    for k, v in sorted(d.items(), key=lambda x: x[0]):
        if isinstance(v, dict):
            print("  " * depth + ("%s" % k))
            print_dict(v, depth + 1)
        else:
            print("  " * depth + f"{k} = {v:.2f}")




def save_plots(figs, instrument, strategy, timestamp):
    for i, fig in enumerate(figs):
        for j, f in enumerate(fig):
            f.savefig(f'output/{strategy.__name__}_{instrument}_{timestamp}_{i}{j}.png', dpi=900, bbox_inches='tight')