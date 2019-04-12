import time
import urllib
import hmac
import hashlib

from requests.auth import AuthBase


def expiration_time(expiration_seconds):
    return int(round(time.time() + expiration_seconds))


# Generates an API signature.
# A signature is HMAC_SHA256(secret, verb + path + nonce + data), hex encoded.
# Verb must be uppercased, url is relative, nonce must be an increasing 64-bit integer
# and the data, if present, must be JSON without whitespace between keys.
#
# For example, in psuedocode (and in real code below):
#
# verb=POST
# url=/api/v1/order
# nonce=1416993995705
# data={"symbol":"XBTZ14","quantity":1,"price":395.01}
# signature = HEX(HMAC_SHA256(secret, 'POST/api/v1/order1416993995705{"symbol":"XBTZ14","quantity":1,"price":395.01}'))
def generate_signature(secret, verb, url, nonce, data):
    """Generate a request signature compatible with BitMEX."""
    # Parse the url so we can remove the base and extract just the path.
    parsed_uri = urllib.parse.urlparse(url)
    path = parsed_uri.path
    if parsed_uri.query:
        path = path + '?' + parsed_uri.query

    if isinstance(data, (bytes, bytearray)):
        data = data.decode('utf8')
    message = (verb + path + str(nonce) + data).encode('utf-8')

    signature = hmac.new(secret.encode('utf-8'), message, digestmod=hashlib.sha256).hexdigest()
    return signature


class APIKeyAuthWithExpires(AuthBase):

    """Attaches API Key Authentication to the given Request object. This implementation uses `expires`."""

    def __init__(self, key, secret, expiration_seconds):
        """Init with Key & Secret."""
        self.api_key = key
        self.api_secret = secret
        self.expiration_seconds = expiration_seconds

    def __call__(self, r):
        """
        Called when forming a request - generates api key headers. This call uses `expires` instead of nonce.

        This way it will not collide with other processes using the same API Key if requests arrive out of order.
        For more details, see https://www.bitmex.com/app/apiKeys
        """
        # modify and return the request
        expires = expiration_time(self.expiration_seconds)
        r.headers['api-expires'] = str(expires)
        r.headers['api-key'] = self.api_key
        r.headers['api-signature'] = generate_signature(self.api_secret, r.method, r.url, expires, r.body or '')

        return r
