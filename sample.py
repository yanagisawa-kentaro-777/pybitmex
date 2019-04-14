import time
from pybitmex import *
from datetime import datetime, timedelta, timezone

bitmex = BitMEXClient(
    "https://www.bitmex.com/api/v1/", "XBTUSD",
    api_key=None, api_secret=None,
    use_websocket=True, use_rest=True,
    subscriptions=["instrument", "orderBookL2", "trade", "margin", "order", "position"]
)
while True:
    time.sleep(3)
    started = datetime.now()

    state = bitmex.ws_market_state()
    print("Market: {}".format(state))

    bids, asks = bitmex.ws_sorted_bids_and_asks_of_market()
    print("{:.1f} & {:.1f} ({:,d} bids and {:,d} asks)".format(
       bids[0]["price"], asks[0]["price"], len(bids), len(asks)
    ))
    print("Boards: {:.2f} seconds".format((datetime.now() - started).total_seconds()))
    last_update = bitmex.get_last_ws_update("orderBookL2")
    print("Last update of boards: {}".format(str(last_update)))

    trades = bitmex.ws_sorted_recent_trade_objects_of_market()
    print("{:,d} recent trades".format(len(trades)))
    print("Last update of trades: {}".format(str(bitmex.get_last_ws_update("trade"))))

    open_orders = bitmex.ws_open_order_objects_of_account()
    print("{:d} open bids and {:d} open asks".format(len(open_orders.bids), len(open_orders.asks)))

    position_size = bitmex.ws_current_position_size()
    print("position: {:,d}".format(position_size))

    withdrawble_balance, wallet_balance = bitmex.ws_balances_of_account_object()
    print("Balance: {:.8f} / {:.8f}".format(withdrawble_balance, wallet_balance))

    end = datetime.now()
    print("Total: {:.2f} seconds".format((end - started).total_seconds()))
    print("")

    #rest_open_orders = bitmex.rest_get_raw_orders_of_account({"open": True})
    #print("REST Open Orders: {}".format(str(rest_open_orders)))

    # filter_obj = bitmex.create_hourly_filter(2019, 4, 14, 1)
    filter_obj = bitmex.create_time_range_filter(datetime.now().astimezone(timezone.utc) -
                                                 timedelta(hours=2), datetime.now().astimezone(timezone.utc))
    print(str(filter_obj))
    rest_trade_history =\
        bitmex.rest_get_raw_trade_history_of_account(filter_obj, count=500)
    print(len(rest_trade_history))
    print(str(rest_trade_history[0]['timestamp']) + " " + (rest_trade_history[-1]['timestamp']))
    #print("")

