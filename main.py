from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import importlib
import matplotlib

matplotlib.use('TkAgg')

import argparse
import datetime
import random

import backtrader as bt
import matplotlib.pyplot as plt

from helpers_functions import print_trade_analysis, print_dict, print_sharpe_ratio, print_sqn, save_trade_analysis
from oanda_functions import get_historical_data_factory


# from strategies import candles, candles_mcd, simple_bollinger


def parse_args():
    parser = argparse.ArgumentParser(description='Customized Strategy')

    parser.add_argument('--from_date', '-f',
                        default='2017-01-01',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--to_date', '-t',
                        default='2018-01-01',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--granularity', default='H4', type=str,
                        help='Granularity of data')

    parser.add_argument('--only_long', '-ol', default=True, action='store_true',
                        help='Do only long operations')

    parser.add_argument('--write_csv', '-wcsv', default=True, action='store_true',
                        help='Tell the writer to produce a csv stream')

    parser.add_argument('--show_plot', '-sp', default=True, action='store_true',
                        help='show plot')

    parser.add_argument('--different_account', '-da', action='store_true',
                        help='Use the same account for all instrument.')

    parser.add_argument('--cash', default=100_000, type=int,
                        help='Starting Cash')

    parser.add_argument('--leverage', default=50, type=int,
                        help='Leverage')

    # Set the commission - 0.1% ... divide by 100 to remove the % ... 0.001
    # forex, set to zero
    parser.add_argument('--commission', default=0.00, type=float,
                        help='Commission for operation')

    # parser.add_argument('--mult', default=10, type=int,
    #                     help='Multiplier for futures')
    #
    # parser.add_argument('--margin', default=2000.0, type=float,
    #                     help='Margin for each future')
    #
    # parser.add_argument('--stake', default=1, type=int,
    #                     help='Stake to apply in each operation')
    #
    # parser.add_argument('--plot', '-p', action='store_true',
    #                     help='Plot the read data')
    #
    # parser.add_argument('--numfigs', '-n', default=1,
    #                     help='Plot using numfigs figures')

    return parser.parse_args()


def start_backtest(strategy, instrument_list=None, session_id=None, show_plot=False):
    if instrument_list is None:
        instrument_list = ["AUD_USD"]
    if session_id is None:
        session_id = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d%H%M%S')

    # parse arguments
    args = parse_args()

    # Create a cerebro entity
    cerebro = bt.Cerebro()
    if args.write_csv:
        cerebro.addwriter(bt.WriterFile, out=f'output/backtest_{timestamp}.csv', csv=True, rounding=2)

    # oanda method 2 (instrument factory)
    params = {
        "from": f"{args.from_date}T00:00:00Z",
        "granularity": args.granularity,
        "to": f"{args.to_date}T00:00:00Z"
    }

    # crypto compare BTC USD
    # from_date = cc.to_seconds_epochjlab(datetime.datetime(2016, 1, 1))
    # to_date = cc.to_seconds_epoch(datetime.datetime(2018, 1, 1))
    # df = cc.get_df(from_date, to_date, time_period='histoday', coin='ETH', data_folder='data')

    data = []
    for i, instrument in enumerate(instrument_list):
        df = get_historical_data_factory(instrument, params)
        data.append(bt.feeds.PandasData(dataname=df, timeframe=bt.TimeFrame.Minutes, compression=240))
        cerebro.adddata(data[i], name=instrument)

    # Set our desired cash start
    cerebro.broker.setcash(args.cash)
    cerebro.broker.set_shortcash(False)

    # Add a strategy
    cerebro.addstrategy(strategy, only_long=args.only_long)

    cerebro.broker.setcommission(commission=args.commission, leverage=args.leverage)
    # cerebro.broker.setcommission(commission=0, leverage=args.leverage)

    # Add a FixedSize sizer according to the stake
    # cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Add the analyzers we are interested in
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
    cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="draw_down")

    # Run over everything
    strategies = cerebro.run()
    first_strategy = strategies[0]

    # print the analyzers
    try:
        print_trade_analysis(first_strategy.analyzers.ta.get_analysis())
        save_trade_analysis(first_strategy.analyzers.ta.get_analysis(), instrument,
                            f'output/analysis_{strategy.__module__}_{session_id}.csv')
        print_sharpe_ratio(first_strategy.analyzers.sharpe.get_analysis())
        print_sqn(first_strategy.analyzers.sqn.get_analysis())
        print_dict(first_strategy.analyzers.draw_down.get_analysis())
    except Exception as e:
        print(e)

    # Get final portfolio Value
    portfolio_value = cerebro.broker.getvalue()

    # Print out the final result
    print(f'Final Portfolio Value: ${portfolio_value:.2f}')
    # print('Final Portfolio Value: ${0:.2f}'.format(portvalue))

    # plt.style.use('seaborn-notebook')
    plt.style.use('tableau-colorblind10')
    plt.rc('grid', color='k', linestyle='-', alpha=0.1)
    plt.rc('legend', loc='best')

    plot_args = dict(style='candlestick', barup='green', bardown='red',
                     # legendindloc='best',
                     # legendloc='upper right',
                     # legendloc='upper right',
                     legenddataloc='upper right',
                     grid=True,
                     #  Format string for the display of ticks on the x axis
                     fmt_x_ticks='%Y-%b-%d %H:%M',
                     # Format string for the display of data points values
                     fmt_x_data='%Y-%b-%d %H:%M',
                     subplot=True,
                     dpi=900,
                     numfigs=1,
                     # plotymargin=10.0,
                     iplot=False)

    # save_plots(figs, instrument, strategy, timestamp)

    #  separate plot by data feed. (if there is more than one)
    if show_plot:
        if len(first_strategy.datas) > 1:
            for i in range(len(first_strategy.datas)):
                for j, d in enumerate(first_strategy.datas):
                    d.plotinfo.plot = i == j  # only one data feed to be plot. others = False
                    # first_strategy.observers.buysell[j].plotinfo.plot = i == j
                cerebro.plot(**plot_args)
        else:
            cerebro.plot(**plot_args)


if __name__ == '__main__':

    # parse arguments
    args = parse_args()
    # get_instruments()
    session_id = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d%H%M%S')
    instruments = ['EUR_USD', 'GBP_USD', 'AUD_USD', 'NZD_USD', 'XAU_USD', 'XAG_USD']
    # instruments = ['EUR_USD']

    strategy_module_name = 'candles'
    strategy_module = importlib.import_module(strategy_module_name)

    if args.different_account:
        # run all instruments at the same time with the same account
        start_backtest(strategy_module.MyStrategy, instruments)
    else:
        # run each instrument independently starting with a new account each
        for instrument in instruments:
            start_backtest(strategy_module.MyStrategy, [instrument], session_id=session_id, show_plot=False)
