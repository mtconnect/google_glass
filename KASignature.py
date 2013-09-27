import base64
import sys

# Prepare hash functions
try:
    # Python 2.5 and newer
    import hashlib
    import hmac

    def compute_md5_hex(data):
        h = hashlib.md5()
        h.update(data)
        return h.hexdigest()

    def compute_sha1_base64(data):
        h = hashlib.sha1()
        h.update(data)
        return base64.b64encode(h.digest())

    def compute_hmac_base64(key, msg, ):
        h = hmac.new(key,digestmod=hashlib.sha1)
        h.update(msg)
        return base64.b64encode(h.digest())

except ImportError:
    # Python 2.4
    import md5
    import sha

    def compute_md5_hex(data):
        h = md5.new()
        h.update(data)
        return h.hexdigest()

    def compute_sha1_base64(data):
        h = sha.new()
        h.update(data)
        return base64.b64encode(h.digest())

# Python 2 vs 3
if sys.hexversion > 0x03000000:
    EOL = b"\n"

    def to_hashable(data):
        """ Convert data to a hashable type. """
        if isinstance(data, bytes):
            return data
        else:
            return str(data).encode()

    def ascii_to_hashable(data):
        """ Convert ASCII text data to a hashable type. """
        if isinstance(data, bytes):
            return data
        else:
            return str(data).encode('ascii')
else:
    EOL = "\n"

    def to_hashable(data):
        """ Convert data to a hashable type. """
        return str(data)

    def ascii_to_hashable(data):
        """ Convert ASCII text data to a hashable type. """
        return str(data)


__all__ = ['KASignature']


class KASignature:
    """ Class generating KA request signatures. """

    def __init__(self, secret_key):
        self.secret_key = ascii_to_hashable(secret_key)

    def sign_with_content_md5(self, method, content_md5, content_type, date, request_path):
        """
        Sign request using MD5 hash of the request content.

        Arguments:
           * method: HTTP verb (e.g. GET) used in the request
           * content_md5: MD5 hash of the content (body) of the request. FIXME empty request (GET)
           * content_type: Content type specified in the request. FIXME empty request (GET)
           * date: Value of the date header sent with the request (as GMT). The
              signature is only valid if the request is performed within 15
              minutes of the specified date.
           * request_path: Path of the destination resource (e.g. /user.xml).
              It has to be URL encoded if necessary.

        Returns the signature as str (Python 2) or bytes (Python 3).
        """

        #print('method '+method)
        #print('content_md5 '+content_md5)
        #print('content_type '+content_type)
        #print('date '+date)
        #print('request_path '+request_path)

        toSign = ascii_to_hashable(method)+EOL
        toSign += ascii_to_hashable(content_md5)+EOL
        if content_type is not None:
            content_type=content_type.split(';')[0]
            toSign += ascii_to_hashable(content_type)+EOL
        else:
            toSign += EOL
        toSign += ascii_to_hashable(date)+EOL
        toSign += ascii_to_hashable(request_path)

        return compute_hmac_base64(self.secret_key, toSign)

    def sign(self, method, content, content_type, date, request_path):
        """
        Sign request using request content.

        The content argument is body of the request. Under Pyton 3, it is
        strongly recommended to pass it as bytes to avoid problems with
        incorrect encoding. See sign_with_content_md5 for the description of
        the remaining arguments.

        Returns the signature as str (Python 2) or bytes (Python 3).
        """
    
        if content is None:
            content_md5=""
        else:
            content_md5 = compute_md5_hex(to_hashable(content))

        print "content md5 "+content_md5

        return self.sign_with_content_md5(method, content_md5, content_type, date, request_path)

   
