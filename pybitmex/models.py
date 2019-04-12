
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
