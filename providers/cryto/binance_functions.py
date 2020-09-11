import random

import pandas as pd
from binance.client import Client

from config.keys import binance_keys
from initialize import APP_PATH
from providers.cryto.get_all import get_all_binance

binance_api_key = binance_keys['api']
binance_api_secret = binance_keys['secret_key']
binance_client = Client(api_key=binance_api_key, api_secret=binance_api_secret)

def get_symbol_info(symbol):
    return binance_client.get_symbol_info(symbol)

def get_random_symbols(n=200, base='BTC'):
    symbols = binance_client.get_all_tickers()
    filtered = filter(lambda x: x['symbol'].endswith(base), symbols)
    samples = random.sample(list(filtered), n)
    final_symbols = []
    for sample in samples:
        df = get_all_binance(sample.get('symbol'), '1d', save=True)
        if df.index[0].year < 2019:
            final_symbols.append(sample.get('symbol'))
    return final_symbols


def get_historical_data(symbol, params):
    filename = f'binance_{symbol}'
    for _, value in params.items():
        filename += '_' + value
    filename += '.csv'

    try:
        df = pd.read_csv(f'{APP_PATH}/data/{filename}')
    except FileNotFoundError:
        dict_crypto = binance_client.get_historical_klines(symbol=symbol, **params)
        columns = ['datetime', 'open', 'high', 'low',
                   'close', 'volume', 'close time', 'quote asset volume',
                   'number of trades', 'taker buy base asset volume',
                   'taker buy quote asset volume', 'ignore']

        df = pd.DataFrame(dict_crypto, columns=columns)
        df.to_csv(f'{APP_PATH}/data/{filename}', index=False)

    df['Asset'] = symbol
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric,
                                                                                                          errors='coerce')
    df.dropna(inplace=True)
    df.set_index('datetime', inplace=True)
    return df[['open', 'high', 'low', 'close', 'volume']]


if __name__ == '__main__':
    # params = dict(interval='4h', start_str='2019-01-01', end_str='2019-03-30')
    # t = get_historical_data('BNBBTC', params)
    # print(t)
    print(get_random_symbols())
