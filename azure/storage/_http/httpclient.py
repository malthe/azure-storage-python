﻿#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import base64
import sys

if sys.version_info < (3,):
    from httplib import (
        HTTP_PORT,
        HTTPS_PORT,
        )
    from urllib2 import quote as url_quote
else:
    from http.client import (
        HTTP_PORT,
        HTTPS_PORT,
        )
    from urllib.parse import quote as url_quote

from . import HTTPError, HTTPResponse

class _HTTPClient(object):

    '''
    Takes the request and sends it to cloud service and returns the response.
    '''

    def __init__(self, protocol=None, session=None, timeout=None):
        '''
        :param str protocol:
            http or https.
        :param requests.Session request_session:
            session object created with requests library (or compatible).
        :param int timeout:
            timeout for the http request, in seconds.
        '''
        self.protocol = protocol
        self.session = session
        self.timeout = timeout

        # By default, requests adds an Accept:*/* and Accept-Encoding to the session, 
        # which causes issues with some Azure REST APIs. Removing these here gives us 
        # the flexibility to add it back on a case by case basis.
        if 'Accept' in self.session.headers:
            del self.session.headers['Accept']

        if 'Accept-Encoding' in self.session.headers:
            del self.session.headers['Accept-Encoding']

        self.proxies = None

    def set_proxy(self, host, port, user, password):
        '''
        Sets the proxy server host and port for the HTTP CONNECT Tunnelling.

        Note that we set the proxies directly on the request later on rather than 
        using the session object as requests has a bug where session proxy is ignored 
        in favor of environment proxy. So, auth will not work unless it is passed 
        directly when making the request as this overrides both.

        :param str host:
            Address of the proxy. Ex: '192.168.0.100'
        :param int port:
            Port of the proxy. Ex: 6000
        :param str user:
            User for proxy authorization.
        :param str password:
            Password for proxy authorization.
        '''
        if user and password:
            proxy_string = '{}:{}@{}:{}'.format(user, password, host, port) 
        else:
            proxy_string = '{}:{}'.format(host, port) 

        self.proxies = {}
        self.proxies['http'] = 'http://{}'.format(proxy_string)
        self.proxies['https'] = 'https://{}'.format(proxy_string)

    def perform_request(self, request):
        '''
        Sends an HTTPRequest to Azure Storage and returns an HTTPResponse. If 
        the response code indicates an error, raise an HTTPError.    
        
        :param HTTPRequest request:
            The request to serialize and send.
        :return: An HTTPResponse containing the parsed HTTP response.
        :rtype: :class:`~azure.storage._http.HTTPResponse`             
        '''
        # Verify the body is in bytes
        if request.body:
            assert isinstance(request.body, bytes)

        # Construct the URI
        uri = self.protocol.lower() + '://' + request.host + request.path

        # Send the request
        response = self.session.request(request.method, 
                                        uri,
                                        params=request.query,
                                        headers=request.headers, 
                                        data=request.body or None,
                                        timeout=self.timeout,
                                        proxies=self.proxies)

        # Parse the response
        status = int(response.status_code)
        respheaders = {}
        for key, name in response.headers.items():
            respheaders[key.lower()] = name

        return HTTPResponse(status, response.reason, respheaders, response.content)