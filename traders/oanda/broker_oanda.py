import pandas as pd
import datetime as dt
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.instruments as instruments
import pytz
from oandapyV20 import API
from oandapyV20.contrib.factories import InstrumentsCandlesFactory
from oandapyV20.contrib.requests import MarketOrderRequest
from oandapyV20.contrib.requests import TakeProfitDetails, StopLossDetails
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.positions as positions
from config.keys import oanda_keys

PRACTICE_API_HOST = 'api-fxpractice.forex.com'
PRACTICE_STREAM_HOST = 'stream-fxpractice.forex.com'
LIVE_API_HOST = 'api-fxtrade.forex.com'
LIVE_STREAM_HOST = 'stream-fxtrade.forex.com'
PORT = '443'


class OandaBroker2:
    # tz = pytz.timezone('America/New_York')

    def __init__(self, account_id, access_token, is_live=False):
        if is_live:
            host = LIVE_API_HOST
            stream_host = LIVE_STREAM_HOST
        else:
            host = PRACTICE_API_HOST
            stream_host = PRACTICE_STREAM_HOST

        self.account_id = account_id
        self.access_token = access_token
        self.client = API(access_token=self.access_token)
        self.support = None
        self.resistance = None

    def get_positions(self):
        r = positions.OpenPositions(accountID=self.account_id)
        self.client.request(r)

        all_positions = r.response.get("positions", [])
        for position in all_positions:
            instrument = position['instrument']
            unrealized_pnl = position['unrealizedPL']
            pnl = position['pl']
            long = position['long']
            short = position['short']

            if short['units']:
                self.on_position_event(
                    instrument, False, short['units'], unrealized_pnl, pnl)
            elif long['units']:
                self.on_position_event(
                    instrument, True, long['units'], unrealized_pnl, pnl)
            else:
                self.on_position_event(
                    instrument, None, 0, unrealized_pnl, pnl)
        return all_positions

    def send_market_order(self, instrument, quantity, is_buy, take_profit=None, stop_loss=None):

        tp = None if take_profit is None else TakeProfitDetails(price=take_profit).data

        sl = None if stop_loss is None else StopLossDetails(price=stop_loss).data

        if is_buy:
            mkt_order = MarketOrderRequest(instrument=instrument,
                                           units=quantity,
                                           takeProfitOnFill=tp,
                                           stopLossOnFill=sl)
        else:
            mkt_order = MarketOrderRequest(instrument=instrument,
                                           units=(quantity * -1),
                                           takeProfitOnFill=tp,
                                           stopLossOnFill=sl)

        r = orders.OrderCreate(self.account_id, data=mkt_order.data)
        self.client.request(r)

        if r.status_code != 201:
            self.on_order_event(instrument, quantity, is_buy, None, 'NOT_FILLED')
            return False

        if 'orderCancelTransaction' in r.response:
            self.on_order_event(instrument, quantity, is_buy, None, 'NOT_FILLED')
            return False

        transaction_id = r.response.get('lastTransactionID', None)
        self.on_order_event(instrument, quantity, is_buy, transaction_id, 'FILLED')
        return r

    def get_prices(self, instruments_, params):
        if isinstance(instruments_, list):
            df_list = []
            for instrument in instruments_:
                df_list.append(self.get_prices(instrument, params))
            return pd.concat(df_list)

        return self.get_prices_instrument(instruments_, params)

    def get_prices_instrument(self, instrument, params):
        """
        @param instrument:
        @param params:
        @return: dataframe of live candles data
        """
        client = self.client
        r = instruments.InstrumentsCandles(instrument=instrument,
                                           params=params)
        client.request(r)
        candles = r.response.get("candles")
        instrument = r.response.get("instrument")
        granularity = r.response.get("granularity")
        df1 = pd.DataFrame(candles)[['complete', 'volume', 'time']]
        df2 = pd.DataFrame(list(pd.DataFrame(candles)['mid']))
        df = pd.concat([df1, df2], axis=1)
        df.rename(mapper={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close'}, inplace=True, axis=1)
        df['time'] = pd.to_datetime(df['time'])
        # df['time'] = df['time'].dt.tz_convert('America/New_York')

        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].apply(pd.to_numeric,
                                                                                          errors='coerce')
        df['instrument'] = instrument
        df['granularity'] = granularity
        return df

    def on_order_event(self, instrument, quantity, is_buy, transaction_id, status):
        print(
            dt.datetime.now(), '[ORDER]',
            'account_id:', self.account_id,
            'transaction_id:', transaction_id,
            'status:', status,
            'instrument:', instrument,
            'quantity:', quantity,
            'is_buy:', is_buy,
        )

    def on_position_event(self, instrument, is_long, units, unrealized_pnl, pnl):
        print(
            dt.datetime.now(), '[POSITION]',
            'account_id:', self.account_id,
            'instrument:', instrument,
            'is_long:', is_long,
            'units:', units,
            'upnl:', unrealized_pnl,
            'pnl:', pnl
        )


if __name__ == '__main__':
    broker = OandaBroker2(account_id=oanda_keys['account_id'], access_token=oanda_keys['access_token'])
    # pos = broker.get_positions()
    # print(pos)
    # for p in pos:
    #     print(p['instrument'], p['long'])
    #     print(p['instrument'], p['short'])
    # order = broker.send_market_order('EUR_USD', 1, True)
    # print(order)

    print(broker.get_positions())
    print('end')
