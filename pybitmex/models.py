
class Trade:

    def __init__(self, _trd_match_id, _timestamp, _side, _price, _size):
        self.trd_match_id = _trd_match_id
        self.timestamp = _timestamp
        self.side = _side
        self.price = _price
        self.size = _size
        # Redundant fields for the convenience of aggregation.
        if self.side == "Buy":
            bought_size = self.size
            sold_size = 0
        else:
            sold_size = self.size
            bought_size = 0
        self.momentum = bought_size - sold_size

    def __str__(self):
        return str(self.to_dict())

    def to_dict(self):
        return {
            'trdMatchID': self.trd_match_id,
            'timestamp': self.timestamp,
            'side': self.side,
            'price': self.price,
            'size': self.size,
            "momentum": self.momentum
        }


class OpenOrder:

    def __init__(self, order_id, client_order_id, side, quantity, price, timestamp):
        self.order_id = order_id
        self.client_order_id = client_order_id
        self.side = side
        self.quantity = quantity
        self.price = price
        self.timestamp = timestamp

    def __str__(self):
        return "Side: {}; Quantity: {:d}; Price: {:.1f}; OrderID: {}; ClOrdID: {}; Timestamp: {}; ".format(
            self.side, self.quantity, self.price, self.order_id, self.client_order_id,
            self.timestamp.strftime("%Y%m%d_%H%M%S")
        )


class OpenOrders:

    def __init__(self, bids, asks):
        self.bids = bids
        self.asks = asks

    def remove_orders(self, remove_targets):
        new_bids = [b for b in self.bids if b.order_id not in remove_targets]
        new_asks = [a for a in self.asks if a.order_id not in remove_targets]
        return OpenOrders(bids=new_bids, asks=new_asks)

    def to_list(self):
        return self.bids + self.asks
