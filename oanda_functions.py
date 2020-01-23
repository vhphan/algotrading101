from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import json
import os

import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.instruments as instruments
import pandas as pd
from oandapyV20 import API
from oandapyV20.contrib.factories import InstrumentsCandlesFactory

from keys import oanda_keys


def get_historical_data(instrument, params):
    # Create a Data Feed
    account_id = oanda_keys['account_id']
    client = API(access_token=oanda_keys['access_token'])

    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    response = client.request(r)
    print("Request: {}  #candles received: {}".format(r, len(r.response.get('candles'))))
    candles = [candle['mid'] for candle in response['candles']]
    ts = [candle['time'] for candle in response['candles']]
    vol = [candle['volume'] for candle in response['candles']]
    candles_df = pd.DataFrame(data=candles)
    ts_df = pd.DataFrame(data=ts)
    vol_df = pd.DataFrame(data=vol)
    df = pd.concat([ts_df, candles_df, vol_df], axis=1)
    df.columns = ['datetime', 'close', 'high', 'low', 'open', 'volume']
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')
    for col in df.columns:
        df[col] = pd.to_numeric(df[col])
    print(df.head())
    return df


def get_instruments():
    account_id = oanda_keys['account_id']
    client = API(access_token=oanda_keys['access_token'])
    r = accounts.AccountInstruments(accountID=account_id)
    rv = client.request(r)
    print(json.dumps(rv, indent=2))
    for item in rv['instruments']:
        if 'USD_' in item['name']:
            print(item['name'])


def get_historical_data_factory(instrument, params):
    # filename
    p_to = params['to'][:10]
    p_from = params['from'][:10]
    p_granularity = params['granularity']
    filename = f"data/data_oanda_{instrument}_{p_from}_{p_to}_{p_granularity}.csv"
    if os.path.isfile(filename):
        df2 = pd.read_csv(filename)
        df2['datetime'] = pd.to_datetime(df2['datetime'])
        df2 = df2.set_index('datetime')
        return df2

    # Create a Data Feed
    account_id = oanda_keys['account_id']
    client = API(access_token=oanda_keys['access_token'])

    df_list = []

    def cnv(response):
        # for candle in response.get('candles'):
        #     print(candle)
        candles = [candle['mid'] for candle in response['candles']]

        ts = pd.DataFrame({'datetime': [candle['time'] for candle in response['candles']]})

        vol = pd.DataFrame({'volume': [candle['volume'] for candle in response['candles']]})

        candles_df = pd.DataFrame(data=candles)
        ts_df = pd.DataFrame(data=ts)
        vol_df = pd.DataFrame(data=vol)

        df = pd.concat([ts_df, candles_df, vol_df], axis=1)
        df.rename({'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close'}, axis=1, inplace=True)

        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col])
        df_list.append(df)

    for r in InstrumentsCandlesFactory(instrument=instrument, params=params):
        # print("FACTORY REQUEST: {} {} {}".format(r, r.__class__.__name__, r.params))
        rv = client.request(r)
        cnv(rv)

    df2 = pd.concat(df_list)
    now = datetime.datetime.now()
    dt_string = now.strftime("%Y%m%d%H%M%S")

    df2.to_csv(filename)

    return df2
