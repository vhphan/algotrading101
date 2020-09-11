# https://medium.com/swlh/retrieving-full-historical-data-for-every-cryptocurrency-on-binance-bitmex-using-the-python-apis-27b47fd8137f

# IMPORTS
import pandas as pd
import math
import os.path
import time

import pendulum as pendulum
from bitmex import bitmex
from binance.client import Client
from datetime import timedelta, datetime
from dateutil import parser
from tqdm import tqdm_notebook  # (Optional, used for progress-bars)

### API
from config.keys import binance_keys

binance_api_key = binance_keys['api']  # Enter your own API-key here
binance_api_secret = binance_keys['secret_key']  # Enter your own API-secret here

### CONSTANTS
binsizes = {"1m": 1, "5m": 5, "1h": 60, "4h": 240, "1d": 1440}
batch_size = 750
binance_client = Client(api_key=binance_api_key, api_secret=binance_api_secret)


### FUNCTIONS
def minutes_of_new_data(symbol, kline_size, data, source):
    if len(data) > 0:
        old = parser.parse(data["timestamp"].iloc[-1])
    elif source == "binance":
        old = datetime.strptime('1 Jan 2017', '%d %b %Y')
    elif source == "bitmex":
        old = \
            bitmex_client.Trade.Trade_getBucketed(symbol=symbol, binSize=kline_size, count=1, reverse=False).result()[
                0][0][
                'timestamp']
    if source == "binance": new = pd.to_datetime(binance_client.get_klines(symbol=symbol, interval=kline_size)[-1][0],
                                                 unit='ms')
    if source == "bitmex": new = \
        bitmex_client.Trade.Trade_getBucketed(symbol=symbol, binSize=kline_size, count=1, reverse=True).result()[0][0][
            'timestamp']
    return old, new


def get_all_binance(symbol, kline_size, save=False):
    filename = f'data/{symbol}-{kline_size}-data.zip'
    if os.path.isfile(filename):
        data_df = pd.read_csv(filename)
    else:
        data_df = pd.DataFrame()
    oldest_point, newest_point = minutes_of_new_data(symbol, kline_size, data_df, source="binance")
    delta_min = (newest_point - oldest_point).total_seconds() / 60
    available_data = math.ceil(delta_min / binsizes[kline_size])
    if oldest_point == datetime.strptime('1 Jan 2017', '%d %b %Y'):
        print('Downloading all available %s data for %s. Be patient..!' % (kline_size, symbol))
    else:
        print('Downloading %d minutes of new data available for %s, i.e. %d instances of %s data.' % (
            delta_min, symbol, available_data, kline_size))
    klines = binance_client.get_historical_klines(symbol, kline_size, oldest_point.strftime("%d %b %Y %H:%M:%S"),
                                                  newest_point.strftime("%d %b %Y %H:%M:%S"))
    data = pd.DataFrame(klines,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av',
                                 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    if len(data_df) > 0:
        temp_df = pd.DataFrame(data)
        data_df = data_df.append(temp_df)
    else:
        data_df = data
    data_df.set_index('timestamp', inplace=True)
    if save:
        archive_name = f'{symbol}-{kline_size}-data.csv'
        compression_options = dict(method='zip', archive_name=archive_name)
        data_df.to_csv(filename, compression=compression_options)

    print('All caught up..!')
    return data_df


if __name__ == '__main__':
    tickers = binance_client.get_all_tickers()
    tickers_base_usdt = [ticker.get('symbol') for ticker in tickers if ticker.get('symbol').endswith('USDT')]
    for symbol in tickers_base_usdt:
        print(f'getting data for {symbol} ...')
        start_time = pendulum.now()
        df = get_all_binance(symbol, '1h', save=True)
        end_time = pendulum.now()
        print('time taken in minutes ', end_time.diff(start_time).in_minutes())
