import time
import json

import logging

import base64
import uuid

import requests

from pybitmex.auth import APIKeyAuthWithExpires


class RestClientError(Exception):
    def __init__(self, message_str, error_code):
        self.message_str = message_str
        self.error_code = error_code
        super(RestClientError, self).__init__(message_str)

    def is_unknown(self):
        return self.error_code < 0

    def is_timeout(self):
        return 999 <= self.error_code

    def is_4xx(self):
        return 400 <= self.error_code < 500

    def is_5xx(self):
        return 500 <= self.error_code < 600


class RestClient:

    def __init__(
            self, uri, api_key=None, api_secret=None,
            symbol="XBTUSD",
            order_id_prefix="",
            agent_name="trading_bot",
            timeout=7,
            expiration_seconds=3600
    ):
        self.logger = logging.getLogger(__name__)

        self.base_url = uri
        self.api_key = api_key
        self.api_secret = api_secret

        self.symbol = symbol
        self.order_id_prefix = order_id_prefix

        # Prepare HTTPS session
        self.session = requests.Session()
        # These headers are always sent
        self.session.headers.update({'user-agent': agent_name})
        self.session.headers.update({'content-type': 'application/json'})
        self.session.headers.update({'accept': 'application/json'})

        self.timeout = timeout
        self.expiration_seconds = expiration_seconds
        self.retries = 0

    def close(self):
        self.session.close()

    def curl_bitmex(self, path, query=None, postdict=None, timeout=None, verb=None, max_retries=None):
        """Send a request to BitMEX Servers."""
        # Handle URL
        uri = self.base_url + path

        if timeout is None:
            timeout = self.timeout

        # Default to POST if data is attached, GET otherwise
        if not verb:
            verb = 'POST' if postdict else 'GET'

        # By default don't retry POST or PUT. Retrying GET/DELETE is okay because they are idempotent.
        # In the future we could allow retrying PUT, so long as 'leavesQty' is not used (not idempotent),
        # or you could change the clOrdID (set {"clOrdID": "new", "origClOrdID": "old"}) so that an amend
        # can't erroneously be applied twice.
        if max_retries is None:
            max_retries = 0 if verb in ['POST', 'PUT'] else 3

        # Auth: API Key/Secret
        auth = APIKeyAuthWithExpires(self.api_key, self.api_secret, self.expiration_seconds)

        def rethrow(message_str, code):
            raise RestClientError(message_str, code)

        def retry(sleep_seconds, code):
            self.retries += 1
            if max_retries < self.retries:
                rethrow("Max retries on {} {} hit.".format(verb, uri), code)

            if 0 <= sleep_seconds:
                seconds_to_sleep = sleep_seconds
            else:
                seconds_to_sleep = self.retries
            time.sleep(seconds_to_sleep)
            return self.curl_bitmex(path, query, postdict, timeout, verb, max_retries)

        # Make the request
        response = None
        try:
            self.logger.info("Requesting %s to %s", verb, uri)
            req = requests.Request(verb, uri, json=postdict, auth=auth, params=query)
            prepped = self.session.prepare_request(req)
            response = self.session.send(prepped, timeout=timeout)
            # Make non-200s throw
            response.raise_for_status()

            # Reset retry counter on success
            self.retries = 0
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response is None:
                rethrow("Unknown Error", -1)

            # 401 - Auth error. This is fatal.
            if response.status_code == 401:
                # Always exit, even if rethrow_errors, because this is fatal
                rethrow(json.dumps(response.json()), response.status_code)
            # 404, can be thrown if order canceled or does not exist.
            elif response.status_code == 404:
                if verb == 'DELETE':
                    return
                rethrow(json.dumps(response.json()), response.status_code)
            # 429, rate limit; cancel orders & wait until X-RateLimit-Reset
            elif response.status_code == 429:
                # Figure out how long we need to wait.
                rate_limit_reset = response.headers['X-RateLimit-Reset']
                to_sleep = int(rate_limit_reset) - int(time.time())
                self.logger.warning("Rate limited. Sleeping %d seconds.", to_sleep)
                time.sleep(to_sleep)

                # Retry the request.
                return retry(0, response.status_code)
            # 503 - BitMEX temporary downtime, likely due to a deploy. Try again
            elif response.status_code == 503:
                error = response.json()['error']
                message = error['message'].lower() if error else ''
                self.logger.info(message)
                return retry(-1, response.status_code)
            elif response.status_code == 400:
                error = response.json()['error']
                message = error['message'].lower() if error else ''
                self.logger.warning(message)
                rethrow(json.dumps(response.json()), response.status_code)
            # If we haven't returned or re-raised yet, we get here.
            rethrow(json.dumps(response.json()), response.status_code)
        except requests.exceptions.Timeout as e:
            # Timeout, re-run this request
            self.logger.info("Request timed out: %s %s", verb, uri)
            return retry(0, 999)
        except requests.exceptions.ConnectionError as e:
            self.logger.warning("Connection error.")
            return retry(3, 999)

    def get_trade_history(self, filter_json_obj, count=500):
        path = 'execution/tradeHistory?count={:d}'.format(count) +\
               '&filter=' + json.dumps(filter_json_obj)
        return self.curl_bitmex(path=path, verb='GET')

    def get_orders_of_account(self, filter_json_obj, count=500):
        path = 'order?count={:d}'.format(count) +\
               '&filter=' + json.dumps(filter_json_obj)
        return self.curl_bitmex(path=path, verb='GET')

    def get_positions_of_account(self, filter_json_obj, count=500):
        path = 'position?count={:d}'.format(count) +\
               '&filter=' + json.dumps(filter_json_obj)
        return self.curl_bitmex(path=path, verb='GET')

    def get_user_margin(self):
        path = 'user/margin'
        return self.curl_bitmex(path=path, verb='GET')

    def place_orders(self, orders, post_only=True, max_retries=None):
        """Create multiple orders."""
        for order in orders:
            if order.get('clOrdID') is None:
                order['clOrdID'] = self.order_id_prefix +\
                                   base64.b64encode(uuid.uuid4().bytes).decode('utf8').rstrip('=\n')
            order['symbol'] = self.symbol
            if post_only:
                order['execInst'] = 'ParticipateDoNotInitiate'
        return self.curl_bitmex(path='order/bulk', postdict={'orders': orders}, verb='POST', max_retries=max_retries)

    def market_close_position(self, order, max_retries=None):
        if order.get('clOrdID') is None:
            order['clOrdID'] = self.order_id_prefix + \
                               base64.b64encode(uuid.uuid4().bytes).decode('utf8').rstrip('=\n')
        order['symbol'] = self.symbol
        order['ordType'] = 'Market'
        order['execInst'] = 'Close'
        return self.curl_bitmex(path='order', postdict=order, verb='POST', max_retries=max_retries)

    def cancel_orders(self, order_id_list, max_retries=None):
        """Cancel an existing order."""
        path = "order"
        postdict = {
            'orderID': order_id_list,
        }
        return self.curl_bitmex(path=path, postdict=postdict, verb="DELETE", max_retries=max_retries)
