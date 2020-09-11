import datetime
import random
import time
import plotly
import cufflinks as cf
import pytz
from plotly.offline import iplot
import plotly.offline as plyo
import pandas as pd
from sqlalchemy import create_engine, text

from config.keys import oanda_keys, connection_strings
from helpers_functions import clean_df_db_dups
from strategies_live.strategy_test import StrategyTest
from traders.oanda.broker_oanda import OandaBroker2

con_str = connection_strings['ep_fx']
engine = create_engine(con_str, echo=False)

# cf.go_offline()
cf.set_config_file(offline=True)


class Trader(object):

    def __init__(self, broker, instruments, granularity, db_engine=None):
        """
        A trading platform
        :param broker: Broker object
        :param instruments: A list of instruments recognized by the broker for trading
        :param strategy: function that takes in latest prices in dataframe and returns orders
        """
        self.broker = broker
        self.granularity = granularity
        self.db_engine = db_engine

        # counter to track number of price event
        self.price_event_counter = 0

        self.positions = None
        self.update_positions()
        self.table_name = "fx_data"

        self.last_timestamp = None
        self.set_last_timestamp()

        if isinstance(instruments, list):
            self.instruments = instruments
        else:
            self.instruments = [instruments]

        self.is_order_pending = False
        self.data = None
        self.run_id = random.randint(1000, 9999)

    def update_positions(self):
        self.positions = self.broker.get_positions()

    def get_position_instrument(self, instrument):
        positions = self.positions
        try:
            pos = filter(lambda x: x.get('instrument') == instrument, positions).__next__()
        except StopIteration as e:
            print(e)
            pos = None
        return pos

    def run_strategy(self):
        self.get_latest_prices()

    def get_latest_prices(self):
        self.set_last_timestamp()
        if self.last_timestamp is None:
            params = dict(granularity=self.granularity, count=1000)
        else:
            unixtime = time.mktime(self.last_timestamp.timetuple())
            params = {'granularity': self.granularity, 'from': unixtime}

        self.update_db(params)

    def update_db(self, params):
        df = self.broker.get_prices(self.instruments, params)
        print('all candles', len(df))
        print('completed candles', len(df[df['complete']]))
        df = df[df['complete']]

        # df['time'] = df.apply(lambda x: self.change_tz(x['time'], tz=pytz.timezone('America/New_York')), axis=1)

        df = clean_df_db_dups(df, self.table_name, self.db_engine, ['time', 'instrument', 'granularity'])
        if len(df) > 0:
            df.to_sql(self.table_name, self.db_engine, if_exists='append', index=False)
            self.set_last_timestamp()

    @staticmethod
    def change_tz(ts, tz=pytz.timezone('America/New_York')):
        y, m, d, h, minute, s = ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second
        return pd.Timestamp(year=y, month=m, day=d, hour=h, minute=minute, second=s, tz=tz)

    def set_last_timestamp(self):
        # get last timestamp from db and set it to property last_timestamp
        sql = f"SELECT Max(time) as last_timestamp from fx_data WHERE granularity='{self.granularity}'"
        df = pd.read_sql(text(sql), self.db_engine)

        if len(df) > 0:
            # self.last_timestamp = df['last_timestamp'].dt.tz_convert('America/New_York').iloc[0]
            if self.last_timestamp != df['last_timestamp'].iloc[0]:
                self.last_timestamp = df['last_timestamp'].iloc[0]
                self.on_price_event()
            return

    def generate_signals(self):
        for instrument in self.instruments:
            sql = f"SELECT * FROM fx_data WHERE instrument='{instrument}' ORDER BY time DESC LIMIT 100"
            df = pd.read_sql(text(sql), self.db_engine)
            self.strategy()

    def candle_plot(self, selected_instrument):

        sql = f"SELECT * FROM fx_data WHERE instrument='{selected_instrument}' ORDER BY time DESC LIMIT 100"
        df = pd.read_sql(text(sql), self.db_engine)

        df.set_index('time', inplace=True)
        qf = cf.QuantFig(df, title=f'{selected_instrument}',
                         legend='right', name=f'{selected_instrument}')
        plyo.iplot(qf.iplot(asFigure=True), image='png', filename=f'{selected_instrument}.html')

    def seconds_elapse_since_last_candle(self):
        now = datetime.datetime.now(pytz.timezone('America/New_York'))
        last = self.change_tz(self.last_timestamp).to_pydatetime()
        delta = now - last
        return delta.seconds

    def seconds_till_next_candle(self):
        return 4 * 3600 - self.seconds_elapse_since_last_candle()

    def sleep_or_run(self):
        s = self.seconds_till_next_candle()
        if s > 0:
            time.sleep(s)
            return
        if s < -10:
            self.get_latest_prices()
            return

    def on_price_event(self):
        self.price_event_counter += 1
        self.update_positions()
        self.generate_signals_and_think()

    def generate_signals_and_think(self):
        for instrument in self.instruments:
            pos = self.get_position_instrument(instrument)
            if not pos:
                sql = f"SELECT * FROM fx_data WHERE instrument='{instrument}' ORDER BY time DESC LIMIT 100"
                df = pd.read_sql(text(sql), self.db_engine)


if __name__ == '__main__':
    broker = OandaBroker2(account_id=oanda_keys['account_id'], access_token=oanda_keys['access_token'])
    trader = Trader(broker, instruments='EUR_USD', granularity='H4', db_engine=engine)
    # trader
    # trader.get_positions()
    # trader.run_strategy()
    # trader.candle_plot('EUR_USD')
    print(trader.last_timestamp)
    trader.get_latest_prices()
    print('end')
    # trader.run_strategy()
