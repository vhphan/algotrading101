from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import importlib
from pathlib import Path
from pprint import pprint

import matplotlib

from bt_args import parse_args

matplotlib.use('TkAgg')

import datetime
import random

import backtrader as bt
import matplotlib.pyplot as plt

from helpers_functions import print_dict, save_trade_analysis, save_analyzers
from providers.forex.oanda_functions import get_historical_data_factory
from providers.cryto.binance_functions import get_historical_data, binance_client, get_symbol_info
import analyzers


def forex_data(instrument, start_str, end_str):
    # forex method 2 (instrument factory)
    params = {
        "from": f"{start_str}T00:00:00Z",
        "granularity": args.granularity,
        "to": f"{end_str}T00:00:00Z"
    }
    return get_historical_data_factory(instrument, params)


def crypto_data(instrument, start_str, end_str=None, interval='4h'):
    # binance
    params = dict(interval=interval, start_str=start_str, end_str=end_str)
    # params = dict(interval='4h', start_str='1 year ago UTC', end_str=end_str)
    return get_historical_data(instrument, params)


def save_plots(cerebro, numfigs=1, iplot=True, start=None, end=None,
               width=16, height=9, dpi=300, tight=True, use=None, file_path='', show=False, **kwargs):
    from backtrader import plot
    # if cerebro.p.oldsync:
    #     plotter = plot.Plot_OldSync(**kwargs)
    # else:
    #     plotter = plot.Plot(**kwargs)
    plotter = plot.Plot(**kwargs)

    figs = []
    for stratlist in cerebro.runstrats:
        for si, strat in enumerate(stratlist):
            rfig = plotter.plot(strat, figid=si * 100,
                                numfigs=numfigs, iplot=iplot,
                                start=start, end=end, use=use)
            figs.append(rfig)

    for fig in figs:
        for f in fig:
            f.set_size_inches(width, height)
            f.savefig(file_path, bbox_inches='tight')
            if show:
                plt.show()
    return figs


# saveplots(cerebro, file_path='savefig.png')  # run it

def start_backtest(strategy, instrument_list, session_id=None, show_plot=False, output_path=None):
    if session_id is None:
        session_id = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d%H%M%S')

    args = parse_args()
    if output_path is None:
        output_path = 'output'
    if not Path(output_path).is_dir():
        Path(output_path).mkdir(parents=True, exist_ok=True)

    # Create a cerebro entity
    cerebro = bt.Cerebro()
    if args.write_csv:
        filename = f'{output_path}/backtest_{timestamp}.csv' if len(
            instrument_list) > 1 else f'{output_path}/backtest_{timestamp}_{instrument_list[0]}.csv'
        # filename = f'{output_path}/backtest_{timestamp}_{instrument_list[0]}.csv'
        cerebro.addwriter(bt.WriterFile, out=filename, csv=True, rounding=2)

    # crypto compare BTC USD
    # from_date = cc.to_seconds_epochjlab(datetime.datetime(2016, 1, 1))
    # to_date = cc.to_seconds_epoch(datetime.datetime(2018, 1, 1))
    # df = cc.get_df(from_date, to_date, time_period='histoday', coin='ETH', data_folder='data')

    data = []
    granularity = args.granularity
    interval = granularity[::-1].lower()
    if granularity == 'H1':
        compression = 60
    if granularity == 'H4':
        compression = 60 * 4

    shorlisted_instruments = []
    i = 0
    for instrument in instrument_list:
        # check if tradeable first
        symbol_info = get_symbol_info(instrument)
        if symbol_info.get('status') != 'TRADING' or \
                not symbol_info.get('isSpotTradingAllowed'):
            continue

        # df = forex_data(instrument, args.start_date, args.end_date)
        try:
            df = crypto_data(instrument, args.from_date, args.to_date, interval=interval)
        except Exception as e:
            print(instrument, e)
            continue
        df.dropna(inplace=True)
        if not df.empty:
            shorlisted_instruments.append(instrument)
            data.append(bt.feeds.PandasData(dataname=df, timeframe=bt.TimeFrame.Minutes, compression=compression))
            cerebro.adddata(data[i], name=instrument)
            i += 1

    # Set our desired cash start
    cerebro.broker.setcash(args.cash)
    cerebro.broker.set_shortcash(False)

    # Add a strategy
    cerebro.addstrategy(strategy, only_long=args.only_long)

    cerebro.broker.setcommission(commission=args.commission, leverage=args.leverage)

    starting_value = cerebro.broker.getvalue()
    print('Starting Portfolio Value: %.2f' % starting_value)

    # Add the analyzers we are interested in
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
    cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="draw_down")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(analyzers.TradeReturn, _name="trade_return")

    # Run over everything
    strategies = cerebro.run()
    first_strategy = strategies[0]

    for analyzer in first_strategy.analyzers:
        analyzer.print()

    save_trade_analysis(
        first_strategy.analyzers,
        shorlisted_instruments,
        f'{output_path}/analysis_{strategy.__module__}_{session_id}.csv',
        starting_value
    )

    current_instrument = shorlisted_instruments[0] if len(shorlisted_instruments) == 1 else 'multiple_instruments'

    save_analyzers(first_strategy, current_instrument,
                   f'{output_path}/analyzers_result_{strategy.__module__}_{session_id}.csv')

    print_dict(first_strategy.analyzers.draw_down.get_analysis())
    portfolio_value = cerebro.broker.getvalue()
    print(f'Final Portfolio Value: ${portfolio_value:.2f}')

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
                     # numfigs=1,
                     # plotymargin=10.0,
                     iplot=False)

    # save_plots(figs, instrument, strategy, timestamp)

    #  separate plot by data feed. (if there is more than one i.e. multiple data feeds)
    if len(first_strategy.datas) > 1:
        for i in range(len(first_strategy.datas)):
            for j, d in enumerate(first_strategy.datas):
                d.plotinfo.plot = i == j
                # only one data feed to be plot. others = False
                # cerebro.plot(**plot_args)
            if show_plot:
                figure = cerebro.plot(**plot_args)
    else:
        # cerebro.plot(**plot_args)
        asset_name = first_strategy.data0._name
        file_plot = f'{output_path}/{strategy.__module__}_{session_id}_{asset_name}.png'
        save_plots(cerebro, file_path=file_plot, dpi=600, show=show_plot)  # run it


if __name__ == '__main__':
    # 😏

    # parse arguments
    args = parse_args()
    # get_instruments()
    session_id = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d%H%M%S')
    all_tickers = binance_client.get_all_tickers()
    instruments = [ticker.get('symbol') for ticker in all_tickers if ticker.get('symbol').endswith('USDT')]
    # instruments = random.sample(instruments, 15)
    print(instruments)
    # instruments = ['BTCUSDT', 'ETHUSDT']
    strategy_module = importlib.import_module(args.strategy_name)

    same_account = args.same_account
    show_plot = args.show_plot
    timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d%H%M%S')
    output_path = f'output/{args.strategy_name}_{timestamp}'

    if same_account:
        # run all instruments at the same time with the same account
        start_backtest(strategy_module.MyStrategy, instruments, show_plot=show_plot, output_path=output_path)
    else:
        # run each instrument independently starting with a new account each
        for instrument in instruments:
            try:
                start_backtest(strategy_module.MyStrategy,
                               [instrument],
                               session_id=session_id,
                               show_plot=show_plot,
                               output_path=output_path)
            except Exception as e:
                print(instrument)
                print(e)

    print('======== Completed ========')
    print('from date', args.from_date)
    print('to date', args.to_date)
    print('time period', args.granularity)
    print('List of instruments:')
    pprint(instruments)
