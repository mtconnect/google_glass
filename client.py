

from StringIO import StringIO
from textwrap import dedent
from urlparse import urlparse
import email.utils
import httplib
import mimetypes
import os
import json
import traceback

from KASignature import KASignature


VERSION = '1.1.0'


# Configuration 
UPLOAD_ENDPOINT = 'https://upload-api.kooaba.com/'
BUCKET_ID = '<enter-bucket-id>' 

DATA_KEY_SECRET_TOKEN = '<enter-secret-token>'

# with KA auth, both http and https are possible
QUERY_ENDPOINT= 'https://query-api.kooaba.com/v4/query'

QUERY_KEY_SECRET_TOKEN = '<enter-secret-token>' 
QUERY_KEY_ID='<enter-key-id>' ## only needed for KA authentication



class BasicAPIClient:
    """ Client for kooaba  API V4. """

    def __init__(self, secret_token, key_id=None):
        self.KA = KASignature(secret_token)
        self.key_id=key_id
        self.secret_token=secret_token


    #### QUERY API   

    def query(self,filename, auth_method='Token'):
        data, content_type = self.data_from_file(filename)
        content_type, body=self.encode_multipart_formdata([],[('image', filename, data)])

        (response, body) = self._send_request('POST', QUERY_ENDPOINT, bytearray(body), content_type, auth_method)
        return json.loads(body)
    


    #### UPLOAD API (subset of available methods)

    def create_item(self, bucket_id, title, refid, json_string):
        url=UPLOAD_ENDPOINT+'api/v4/buckets/'+bucket_id+'/items'

        metadata=json.loads(json_string)
        data= {"title":title, "reference_id":refid, "metadata":metadata}

        (response, body) = self._send_request('POST', url, json.dumps(data), 'application/json')
        return json.loads(body)


    def attach_image(self, bucket_id, item_id, content_type, data):
        url=UPLOAD_ENDPOINT+'api/v4/items/'+item_id+'/images'

        (response, body) = self._send_request('POST', url, bytearray(data), content_type)
        return json.loads(body)

   
    def replace_metadata(self, item_id, json_string):
        url=UPLOAD_ENDPOINT+'api/v4/items/'+item_id
        metadata=json.loads(json_string)
        data= {"metadata": metadata}
        (response, body) = self._send_request('PUT', url, json.dumps(data), 'application/json')
        return json.loads(body)

    
    ## HELPER METHODS
    
    def data_from_file(self,filename):
        content_type, _encoding = mimetypes.guess_type(filename)
        with open(filename, 'rb') as f:
            return f.read() , content_type

    def _send_request(self, method, api_path, data=None, content_type=None, auth_method='Token'):
        """ Send (POST/PUT/GET/DELETE according to the method) data to an API
        node specified by api_path.

        Returns tuple (response, body) as returned by the API call. The
        response is a HttpResponse object describint HTTP headers and status
        line.

        Raises exception on error:
            - IOError: Failure performing HTTP call
            - RuntimeError: Unsupported transport scheme.
            - RuntimeError: API call returned an error.
        """
        if True:
            if data is None:
               sys.stderr.write( " > " + method +' '+ api_path) 
            elif len(data) < 4096:
                print " > %s ...%s:\n > %s" % (method, api_path, data)
            else:
                print " > %s ...%s: %sB" % (method, api_path, len(data))
        
        parsed_url = urlparse(api_path)
        
        if ((parsed_url.scheme != 'https') and (parsed_url.scheme != 'http')):
            raise RuntimeError("URL scheme '%s' not supported" % parsed_url.scheme)
       
        port = parsed_url.port
        if port is None:
            port=80 
            if (parsed_url.scheme == 'https'):
               port = 443

        host = parsed_url.hostname

        if (parsed_url.scheme == 'https'):
            http = httplib.HTTPSConnection(host, port )
        
        elif (parsed_url.scheme == 'http'):
            http = httplib.HTTPConnection(host, port )

        else:
            raise RuntimeError("URL scheme '%s' not supported" % parsed_url.scheme)
        
        try:
            date = email.utils.formatdate(None, localtime=False, usegmt=True)

            if auth_method=='KA':
                signature = self.KA.sign(method, data, content_type, date, parsed_url.path)
                headers = {'Authorization': 'KA %s:%s' % (self.key_id,signature),'Date': date}
                print "signature: "+headers['Authorization']

            else: # Token
                headers = {'Authorization': 'Token %s' % (self.secret_token),'Date': date}

            if content_type is not None:
                headers['Content-Type'] = content_type
            if data is not None:
                headers['Content-Length'] = str(len(data))
            try:
                http.request(method, parsed_url.path, body=data,  headers=headers)
            except Exception, e:
                raise  #IOError("Error during request: %s: %s" % (type(e), e))
            response = http.getresponse()
            # we have to read the response before the http connection is closed
            body = response.read()
            if True:
                sys.stderr.write( " < " + str(response.status) + ' ' + str(response.reason)+'\n')
                sys.stderr.write( " < " + body+'\n')
            if (response.status < 200) or (response.status > 299):
                raise RuntimeError("API call returned status %s %s. Message: %s" % (response.status, response.reason, body))
            return (response, body)
        finally:
            http.close()


    def encode_multipart_formdata(self, fields, files):
        """
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return (content_type, body) ready for httplib.HTTP instance
        """
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L = []
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % self.get_content_type(filename))
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body

    def get_content_type(self, filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream' 


### example usage of api
def main():

    query_example()
    #upload_example()


def query_example():

    #simple example of KA signature
    signer=KASignature('aSecretKey')
    signature=signer.sign('POST', 'aBody','text/plain', 'Sun, 06 Nov 1994 08:49:37 GMT', '/v2/query')
    print signature
    print 'expected: '+'6XVAzB+hA9JEFWZdg+1ssZ+gfRo='
    
    # perform an actual request
    client = BasicAPIClient(QUERY_KEY_SECRET_TOKEN, QUERY_KEY_ID)
   
    try:
       result =client.query('../images/query_image.jpg', 'KA')

    except:
       print "call failed:" , sys.exc_info()
       traceback.print_exc()


def upload_example():

    client = BasicAPIClient(DATA_KEY_SECRET_TOKEN)

    # loading an image into memory
    data, content_type = client.data_from_file('../images/db_image.jpg')
    
    try:
       item =client.create_item(BUCKET_ID, 'aTitle', 'myRefId', '{}')
       print 'created item '+item['uuid']
       images=client.attach_image(BUCKET_ID, item['uuid'], content_type, data)
       print 'attached image '+images[0]['sha1']
    except:
       print "Upload failed:", sys.exc_info()
       traceback.print_exc()



if __name__ == '__main__':
    import sys
    sys.exit(main())

