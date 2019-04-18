import logging
from datetime import datetime, timezone
from dateutil.parser import parse

from pybitmex import ws, rest, models


class BitMEXClient:

    def __init__(
            self,
            uri="https://testnet.bitmex.com/api/v1/",
            symbol="XBTUSD",
            api_key=None,
            api_secret=None,
            use_websocket=True,
            use_rest=True,
            subscriptions=None,
            order_id_prefix="",
            agent_name="trading_bot",
            http_timeout=7,
            expiration_seconds=3600,
            ws_refresh_interval_seconds=600
    ):
        self.logger = logging.getLogger(__name__)

        self.uri = uri
        self.symbol = symbol
        self.is_running = True
        if use_websocket:
            self.ws_client = ws.BitMEXWebSocketClient(
                endpoint=uri,
                symbol=symbol,
                api_key=api_key,
                api_secret=api_secret,
                subscriptions=subscriptions,
                expiration_seconds=expiration_seconds
            )
            self.ws_refresh_interval_seconds = ws_refresh_interval_seconds
        else:
            self.ws_client = None

        if use_rest:
            self.rest_client = rest.RestClient(
                uri=uri,
                api_key=api_key,
                api_secret=api_secret,
                symbol=symbol,
                order_id_prefix=order_id_prefix,
                agent_name=agent_name,
                timeout=http_timeout,
                expiration_seconds=expiration_seconds
            )
        else:
            self.rest_client = None
        self.order_id_prefix = order_id_prefix

    def close(self):
        self.is_running = False

        if self.ws_client:
            self.ws_client.exit()

        if self.rest_client:
            self.rest_client.close()

    def get_last_ws_update(self, table_name):
        return self.ws_client.updates.get(table_name)

    def _select_ws_client(self, table_name):
        return self.ws_client

    def ws_raw_instrument(self):
        return self._select_ws_client('instrument').get_instrument()

    def ws_market_state(self):
        instrument = self.ws_raw_instrument()
        return instrument["state"]

    def is_market_in_normal_state(self):
        state = self.ws_market_state()
        return state == "Open" or state == "Closed"

    def ws_raw_order_books_of_market(self):
        table_name = self.ws_client.get_order_book_table_name()
        return self._select_ws_client(table_name).market_depth()

    def ws_sorted_bids_and_asks_of_market(self):
        depth = self.ws_raw_order_books_of_market()
        bids = sorted([b for b in depth if b["side"] == "Buy"], key=lambda b: b["price"], reverse=True)
        asks = sorted([b for b in depth if b["side"] == "Sell"], key=lambda b: b["price"], reverse=False)

        def prune(order_books):
            return [{"price": float(each["price"]), "size": int(each["size"])} for each in order_books]

        return prune(bids), prune(asks)

    def ws_raw_recent_trades_of_market(self):
        return self._select_ws_client('trade').recent_trades()

    def ws_sorted_recent_trade_objects_of_market(self, reverse=False):
        raw_trades = self.ws_raw_recent_trades_of_market()
        result = [models.Trade(t["trdMatchID"], parse(t["timestamp"]).astimezone(timezone.utc),
                  t["side"], float(t["price"]), int(t["size"])) for t in raw_trades]
        return sorted([t for t in result], key=lambda t: (t.timestamp, t.trd_match_id), reverse=reverse)

    def ws_raw_current_position(self):
        """
        [{'account': XXXXX, 'symbol': 'XBTUSD', 'currency': 'XBt', 'underlying': 'XBT',
         'quoteCurrency': 'USD', 'commission': 0.00075, 'initMarginReq': 0.01,
         'maintMarginReq': 0.005, 'riskLimit': 20000000000, 'leverage': 100, 'crossMargin': True,
        'deleveragePercentile': None, 'rebalancedPnl': 0, 'prevRealisedPnl': 0,
        'prevUnrealisedPnl': 0, 'prevClosePrice': 3972.24,
        'openingTimestamp': '2019-03-25T07:00:00.000Z', 'openingQty': 0, 'openingCost': 0, 'openingComm': 0,
        'openOrderBuyQty': 0, 'openOrderBuyCost': 0, 'openOrderBuyPremium': 0, 'openOrderSellQty': 0,
        'openOrderSellCost': 0, 'openOrderSellPremium': 0, 'execBuyQty': 0,
        'execBuyCost':0, 'execSellQty': 30, 'execSellCost': 756060, 'execQty': -30, 'execCost': 756060,
        'execComm': -189, 'currentTimestamp': '2019-03-25T07:27:06.107Z',
        'currentQty': -30, 'currentCost': 756060, 'currentComm': -189, 'realisedCost': 0,
        'unrealisedCost': 756060, 'grossOpenCost': 0, 'grossOpenPremium': 0,
        'grossExecCost': 756060, 'isOpen': True, 'markPrice': 3964.82, 'markValue': 756660,
        'riskValue': 756660, 'homeNotional': -0.0075666, 'foreignNotional': 30, 'posState': '',
        'posCost': 756060, 'posCost2': 756060, 'posCross': 0, 'posInit': 7561, 'posComm': 573,
        'posLoss': 0, 'posMargin': 8134, 'posMaint': 4712, 'posAllowance': 0,
        'taxableMargin': 0, 'initMargin': 0, 'maintMargin': 8734, 'sessionMargin': 0,
        'targetExcessMargin': 0, 'varMargin': 0, 'realisedGrossPnl': 0, 'realisedTax': 0,
        'realisedPnl': 189, 'unrealisedGrossPnl': 600, 'longBankrupt': 0, 'shortBankrupt': 0,
        'taxBase': 0, 'indicativeTaxRate': None, 'indicativeTax': 0, 'unrealisedTax': 0,
        'unrealisedPnl': 600, 'unrealisedPnlPcnt': 0.0008, 'unrealisedRoePcnt': 0.0794,
        'simpleQty': None, 'simpleCost': None, 'simpleValue': None, 'simplePnl': None,
        'simplePnlPcnt': None, 'avgCostPrice': 3968, 'avgEntryPrice': 3968,
        'breakEvenPrice':3968.5, 'marginCallPrice': 100000000, 'liquidationPrice': 100000000,
        'bankruptPrice': 100000000, 'timestamp': '2019-03-25T07:27:06.107Z', 'lastPrice': 3964.82,
        'lastValue': 756660}]
        """
        return self._select_ws_client('position').positions()

    def ws_current_position_size(self):
        json_array = self.ws_raw_current_position()
        for each in json_array:
            if each["symbol"] == self.symbol:
                return int(each["currentQty"])
        return 0

    def ws_raw_open_orders_of_account(self):
        return self._select_ws_client('order').open_orders(self.order_id_prefix)

    def ws_open_order_objects_of_account(self):
        """
        [{'orderID': '57180f5f-d16a-62d6-ff8d-d1430637a8d9',
        'clOrdID': '', 'clOrdLinkID': '',
        'account': XXXXX, 'symbol': 'XBTUSD', 'side': 'Sell',
        'simpleOrderQty': None,
        'orderQty': 30, 'price': 3968,
        'displayQty': None, 'stopPx': None, 'pegOffsetValue': None,
        'pegPriceType': '', 'currency': 'USD', 'settlCurrency': 'XBt',
        'ordType': 'Limit', 'timeInForce': 'GoodTillCancel',
        'execInst': 'ParticipateDoNotInitiate', 'contingencyType': '',
        'exDestination': 'XBME', 'ordStatus': 'New', 'triggered': '',
        'workingIndicator': True, 'ordRejReason': '', 'simpleLeavesQty': None,
        'leavesQty': 30, 'simpleCumQty': None, 'cumQty': 0, 'avgPx': None,
        'multiLegReportingType': 'SingleSecurity', 'text': 'Submission from www.bitmex.com',
        'transactTime': '2019-03-25T07:10:34.290Z', 'timestamp': '2019-03-25T07:10:34.290Z'}]
        """
        # clOrdID, orderID, side, orderQty, price
        def order_obj_from_json(json):
            return models.OpenOrder(
                json["orderID"], json["clOrdID"],
                json["side"], json["orderQty"], json["price"],
                parse(json["timestamp"]).astimezone(timezone.utc)
            )

        json_array = self.ws_raw_open_orders_of_account()
        bids = [order_obj_from_json(each) for each in json_array if each["side"] == "Buy"]
        asks = [order_obj_from_json(each) for each in json_array if each["side"] == "Sell"]
        return models.OpenOrders(
            bids=sorted(bids, key=lambda o: o.price, reverse=True),
            asks=sorted(asks, key=lambda o: o.price, reverse=False)
        )

    def ws_recent_trades_of_account(self):
        """
        [{'execID': '0e14ddd0-702d-7338-82d8-fd4c1a419d03',
        'orderID': '57180f5f-d16a-62d6-ff8d-d1430637a8d9',
        'clOrdID': '', 'clOrdLinkID': '', 'account': XXXXX,
        'symbol':'XBTUSD', 'side': 'Sell', 'lastQty': 30, 'lastPx': 3968,
        'underlyingLastPx': None, 'lastMkt': 'XBME', 'lastLiquidityInd': 'AddedLiquidity',
        'simpleOrderQty': None, 'orderQty': 30, 'price': 3968,
        'displayQty': None, 'stopPx': None, 'pegOffsetValue': None,
        'pegPriceType': '', 'currency': 'USD', 'settlCurrency': 'XBt', 'execType': 'Trade',
        'ordType': 'Limit', 'timeInForce': 'GoodTillCancel', 'execInst': 'ParticipateDoNotInitiate',
        'contingencyType': '', 'exDestination': 'XBME',
        'ordStatus': 'Filled', 'triggered': '', 'workingIndicator': False,
        'ordRejReason': '', 'simpleLeavesQty': None, 'leavesQty': 0, 'simpleCumQty': None, 'cumQty':30,
        'avgPx': 3968, 'commission': -0.00025, 'tradePublishIndicator': 'PublishTrade',
        'multiLegReportingType': 'SingleSecurity', 'text': 'Submission from www.bitmex.com',
        'trdMatchID': '34137715-0068-a923-4685-6dbc70e6d2ac', 'execCost': 756060,
        'execComm': -189, 'homeNotional': -0.0075606, 'foreignNotional': 30,
        'transactTime': '2019-03-25T07:26:06.334Z', 'timestamp': '2019-03-25T07:26:06.334Z'}]
         """
        return self._select_ws_client('execution').executions()

    def ws_raw_balances_of_account(self):
        return self._select_ws_client('margin').funds()

    def ws_balances_of_account_object(self):
        """
        {'account': XXXXX, 'currency': 'XBt', 'riskLimit': 1000000000000, 'prevState': '',
        'state': '', 'action': '', 'amount': 377084143, 'pendingCredit': 0, 'pendingDebit': 0,
        'confirmedDebit': 0, 'prevRealisedPnl': 1038, 'prevUnrealisedPnl': 0, 'grossComm': -567,
        'grossOpenCost': 0, 'grossOpenPremium': 0, 'grossExecCost': 756345, 'grossMarkValue': 756090,
        'riskValue': 756090, 'taxableMargin': 0, 'initMargin': 0, 'maintMargin': 8142,
        'sessionMargin': 0, 'targetExcessMargin': 0, 'varMargin': 0, 'realisedPnl': 1227,
        'unrealisedPnl': -540, 'indicativeTax': 0, 'unrealisedProfit': 0, 'syntheticMargin': None,
        'walletBalance': 377085370, 'marginBalance': 377084830, 'marginBalancePcnt': 1,
        'marginLeverage': 0.0020050925941518254, 'marginUsedPcnt': 0, 'excessMargin': 377076688,
        'excessMarginPcnt': 1, 'availableMargin': 377076688, 'withdrawableMargin': 377076688,
        'timestamp': '2019-03-25T07:56:25.462Z', 'grossLastValue': 756090, 'commission': None}
        """
        satoshis_for_btc = 100000000
        data = self.ws_raw_balances_of_account()
        withdrawable_balance = float(data['withdrawableMargin']) / satoshis_for_btc
        wallet_balance = float(data['walletBalance']) / satoshis_for_btc
        return withdrawable_balance, wallet_balance

    def rest_place_orders(self, new_order_list, post_only=True, max_retries=None):
        if len(new_order_list) == 0:
            return
        self.rest_client.place_orders([o for o in new_order_list], post_only=post_only, max_retries=max_retries)

    def rest_market_close_position(self, order, max_retries=None):
        self.rest_client.market_close_position(order, max_retries=max_retries)

    def rest_cancel_orders(self, order_id_list, max_retries=None):
        if len(order_id_list) == 0:
            return
        self.rest_client.cancel_orders(order_id_list, max_retries=max_retries)

    def rest_cancel_all_orders(self):
        open_orders = self.ws_open_order_objects_of_account()
        self.rest_cancel_orders([o.order_id for o in open_orders.to_list()])

    def rest_get_raw_orders_of_account(self, filter_json_obj, count=500):
        return self.rest_client.get_orders_of_account(filter_json_obj, count)

    def rest_get_raw_positions_of_account(self, filter_json_obj, count=500):
        return self.rest_client.get_positions_of_account(filter_json_obj, count)

    def rest_get_raw_trade_history_of_account(self, filter_json_obj, count=500):
        trades = self.rest_client.get_trade_history(filter_json_obj, count)
        return [t for t in trades if t['symbol'] == self.symbol and t['execType'] == 'Trade']

    def rest_get_raw_margin_of_account(self):
        return self.rest_client.get_user_margin()

    @staticmethod
    def create_daily_filter(year, month, day):
        return {"timestamp.date": "{:04}-{:02}-{:02}".format(year, month, day)}

    @staticmethod
    def create_hourly_filter(year, month, day, hour):
        result = BitMEXClient.create_daily_filter(year, month, day)
        result['timestamp.hh'] = "{:02}".format(hour)
        return result

    @staticmethod
    def create_minutely_filter(year, month, day, hour, minute):
        result = BitMEXClient.create_daily_filter(year, month, day)
        result['timestamp.hh'] = "{:02}".format(hour)
        result['timestamp.uu'] = "{:02}".format(minute)
        return result

    @staticmethod
    def create_time_range_filter(start_dt: datetime, end_dt: datetime):
        result = {}
        if start_dt:
            result['startTime'] = start_dt.strftime("%Y-%m-%d %H:%M:%S")
        if end_dt:
            result['endTime'] = end_dt.strftime("%Y-%m-%d %H:%M:%S")
        return result
