import argparse


def parse_args():
    parser = argparse.ArgumentParser(description='Customized Strategy')

    parser.add_argument('--strategy_name', '-sn', default='buy_top_performer')

    parser.add_argument('--from_date', '-f',
                        default='2019-01-01',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--to_date', '-t',
                        default='2019-12-31',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--granularity', default='H1', type=str,
                        help='Granularity of data')

    parser.add_argument('--only_long', '-ol', default=True, action='store_true',
                        help='Do only long operations')

    parser.add_argument('--write_csv', '-wcsv', default=True, action='store_true',
                        help='Tell the writer to produce a csv stream')

    parser.add_argument('--show_plot', '-sp', default=True, action='store_true',
                        help='show plot')

    parser.add_argument('--same_account', '-da', default=True, action='store_false',
                        help='Use the same account for all instrument. Otherwise different account for each instrument')

    parser.add_argument('--cash', default=1_000, type=int,
                        help='Starting Cash')

    parser.add_argument('--leverage', default=50, type=int,
                        help='Leverage')

    # Set the commission - 0.1% ... divide by 100 to remove the % ... 0.001
    # forex, set to zero
    # :airp

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

    return parser.parse_args(args=[])