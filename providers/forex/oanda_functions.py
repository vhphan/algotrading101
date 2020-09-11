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
from oandapyV20.contrib.requests import MarketOrderRequest
import oandapyV20.endpoints.orders as orders

from config.keys import oanda_keys

account_id = oanda_keys['account_id']
access_token = oanda_keys['access_token']



def get_historical_data(instrument, params):
    # Create a Data Feed
    client = API(access_token=access_token)

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
    client = API(access_token=access_token)
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
    client = API(access_token=access_token)

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


def get_live_candles(instrument, params):
    """

    @param instrument:
    @param params:
    @return: dataframe of live candles data
    """
    client = API(access_token=access_token)
    r = instruments.InstrumentsCandles(instrument=instrument,
                                       params=params)
    client.request(r)
    candles = r.response.get("candles")
    data = []
    df1 = pd.DataFrame(candles)[['complete', 'volume', 'time']]
    df2 = pd.DataFrame(list(pd.DataFrame(candles)['mid']))
    df = pd.concat([df1, df2], axis=1)
    df.rename(mapper={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close'}, inplace=True, axis=1)
    df['time'] = pd.to_datetime(df['time'])
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].apply(pd.to_numeric, errors='coerce')
    return df


def order_long(instrument, units, take_profit=None, stop_loss=None):
    api = API(access_token=oanda_keys['access_token'])
    mkt_order_long = MarketOrderRequest(instrument=instrument,
                                        units=units,
                                        takeProfitOnFill=take_profit,
                                        stopLossOnFill=stop_loss)

    r = orders.OrderCreate(oanda_keys['account_id'], data=mkt_order_long.data)
    api.request(r)
    return r.response
    print("Trade Executed")


def get_account_info():
    """

    @return: account details
    """
    r = accounts.AccountDetails(account_id)
    client = API(access_token=access_token)
    rv = client.request(r)
    details = rv.get('account')
    # return details.get('openTradeCount')
    return details


def get_positions():
    """
    @return: list of positiions
    """
    r = accounts.AccountDetails(account_id)
    client = API(access_token=access_token)
    rv = client.request(r)
    return rv.get('account').get('positions')


if __name__ == '__main__':
    instrument = 'EUR_USD'
    # test 1 get candles
    count = 55
    params = {
        "count": count,
        "granularity": "H4"
    }
    t = get_live_candles('EUR_USD', params)

    # test 2 buy instrumen
    # order_long(instrument, 1)

    # get current position
    trade = get_account_info()

    #
    print(trade)
