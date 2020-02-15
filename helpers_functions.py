from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import csv
import math
import os

import backtrader as bt
import pandas as pd
import pyfolio as pf

from functools import reduce


# from benedict import benedict


def save_analyzers_excel(strategy, instrument, excel_file):
    writer = pd.ExcelWriter(excel_file, engine='xlsxwriter')

    for i, analyzer in enumerate(strategy.analyzers):
        results = dict(instrument=instrument)
        analysis = dict()
        analyzer_name = type(analyzer).__name__
        analysis[analyzer_name] = analyzer.get_analysis()
        if analyzer_name == 'PyFolio':
            pass
            # returns, positions, transactions, gross_lev = analyzer.get_pf_items()
            # pf.create_full_tear_sheet(
            #     returns,
            #     positions=positions,
            #     transactions=transactions,
            #     gross_lev=gross_lev,
            #     round_trips=True)
        else:
            results.update(flatten_dict(analysis))

        results_df = pd.DataFrame.from_dict(results, orient='index')
        results_df.to_excel(writer, sheet_name=analyzer_name)


def save_analyzers(strategy, instrument, csv_file):
    results = dict(instrument=instrument)
    for i, analyzer in enumerate(strategy.analyzers):
        analysis = dict()
        analysis[type(analyzer).__name__] = analyzer.get_analysis()
        if type(analyzer).__name__ == 'PyFolio':
            pass
            # returns, positions, transactions, gross_lev = analyzer.get_pf_items()
            # pf.create_full_tear_sheet(
            #     returns,
            #     positions=positions,
            #     transactions=transactions,
            #     gross_lev=gross_lev,
            #     round_trips=True)
        else:
            results.update(flatten_dict(analysis))

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


# code to convert ini_dict to flattened dictionary
# default seperater '_'
def flatten_dict(dd, separator='_', prefix=''):
    return {prefix + separator + k if prefix else k: v
            for kk, vv in dd.items()
            for k, v in flatten_dict(vv, separator, kk).items()
            } if isinstance(dd, dict) else {prefix: dd}


def divide(n, d):
    return n / d if d else 0


# https://stackoverflow.com/questions/25833613/python-safe-method-to-get-value-of-nested-dictionary
def deep_get(dictionary, keys, default=None):
    return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("."), dictionary)


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
    avg_win_ = deep_get(analyzer, 'won.pnl.average', default=0)
    avg_loss_ = deep_get(analyzer, 'lost.pnl.average', default=0)
    total_open_ = deep_get(analyzer, 'total.open', default=0)
    total_closed_ = deep_get(analyzer, 'total.closed', default=0)
    total_won_ = deep_get(analyzer, 'won.total', default=0)
    total_lost_ = deep_get(analyzer, 'lost.total', default=0)
    win_streak_ = deep_get(analyzer, 'streak.won.longest', default=0)
    lose_streak_ = deep_get(analyzer, 'streak.lost.longest', default=0)
    pnl_net_total_ = deep_get(analyzer, 'pnl.net.total', default=0)

    profit_ratio_ = round(divide(total_won_, total_lost_), 3)

    results = dict(
        instrument=instrument,
        total_open=total_open_,
        total_closed=total_closed_,
        total_won=total_won_,
        total_lost=total_lost_,
        win_streak=win_streak_,
        lose_streak=lose_streak_,
        pnl_net=round(pnl_net_total_, 2),
        strike_rate=round(divide(total_won_, total_lost_), 3),
        avg_win=avg_win_,
        avg_loss=avg_loss_,
        profit_ratio=profit_ratio_,
        # expectancy=(1 + divide(avg_win_, abs(avg_loss_))) * profit_ratio_ - 1,
        expectancy=(avg_win_ * total_won_ / total_closed_) + (avg_loss_ * total_lost_ / total_closed_)
    )
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
