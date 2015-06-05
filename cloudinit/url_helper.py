# Copyright (C) 2015 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# vi: ts=4 expandtab

import logging
import time

try:
    from time import monotonic as now
except ImportError:
    from time import time as now

import requests
from requests import exceptions

import six
from six.moves.urllib.parse import quote as urlquote  # noqa
from six.moves.urllib.parse import urlparse  # noqa
from six.moves.urllib.parse import urlunparse  # noqa

from cloudinit import version

LOG = logging.getLogger(__name__)

if six.PY2:
    import httplib
    NOT_FOUND = httplib.NOT_FOUND
    OK = httplib.OK
    _MULTIPLE_CHOICES = httplib.MULTIPLE_CHOICES
    _BAD_REQUEST = httplib.BAD_REQUEST
else:
    import http.client
    NOT_FOUND = http.client.NOT_FOUND
    OK = http.client.OK
    _MULTIPLE_CHOICES = http.client.MULTIPLE_CHOICES
    _BAD_REQUEST = http.client.BAD_REQUEST


SSL_ENABLED = True
try:
    import ssl as _ssl  # noqa
except ImportError:
    SSL_ENABLED = False


def _clean_url(url):
    parsed_url = list(urlparse(url, scheme='http'))
    if not parsed_url[1] and parsed_url[2]:
        # Swap these since this seems to be a common
        # occurrence when given urls like 'www.google.com'
        parsed_url[1] = parsed_url[2]
        parsed_url[2] = ''
    return urlunparse(parsed_url)


def combine_url(base, *add_ons):
    """Creates a url from many pieces."""

    def combine_single(url, add_on):
        url_parsed = list(urlparse(url))
        path = url_parsed[2]
        if path and not path.endswith("/"):
            path += "/"
        path += urlquote(str(add_on), safe="/:")
        url_parsed[2] = path
        return urlunparse(url_parsed)

    url = base
    for add_on in add_ons:
        url = combine_single(url, add_on)
    return url


# Made to have same accessors as UrlResponse so that the
# read_file_or_url can return this or that object and the
# 'user' of those objects will not need to know the difference.
class StringResponse(object):
    def __init__(self, contents, code=OK, encoding='utf-8'):
        self.code = code
        self.headers = {}
        self.url = None
        self.encoding = encoding
        # Get the contents and text in the right encoding(s)...
        if not isinstance(contents, six.text_type):
            self.contents = contents
            self.text = contents.decode(encoding)
        else:
            self.text = contents
            self.contents = contents.encode(encoding)

    def ok(self, *args, **kwargs):
        return self.code == OK

    def __str__(self):
        """The text/unicode contents."""
        return self.text


class FileResponse(StringResponse):
    def __init__(self, path, contents, code=OK, encoding='utf-8'):
        super(FileResponse, self).__init__(self, contents,
                                           code=code, encoding=encoding)
        self.url = path


class UrlResponse(object):
    def __init__(self, response):
        self._response = response

    @property
    def contents(self):
        """The binary contents."""
        return self._response.content

    def text(self):
        """The text/unicode contents."""
        return self._response.text

    @property
    def url(self):
        return self._response.url

    def ok(self, redirects_ok=False):
        upper = _MULTIPLE_CHOICES
        if redirects_ok:
            upper = _BAD_REQUEST
        return self.code >= OK and self.code < upper

    @property
    def headers(self):
        return self._response.headers

    @property
    def code(self):
        return self._response.status_code

    def __str__(self):
        return self.text


class UrlError(IOError):
    def __init__(self, cause, code=None, headers=None):
        IOError.__init__(self, str(cause))
        self.cause = cause
        self.code = code
        self.headers = headers or {}


def _get_ssl_args(url, ssl_details):
    ssl_args = {}
    scheme = urlparse(url).scheme
    if scheme == 'https' and ssl_details:
        if not SSL_ENABLED:
            LOG.warn("SSL is not supported, "
                     "cert. verification can not occur!")
        else:
            if 'ca_certs' in ssl_details and ssl_details['ca_certs']:
                ssl_args['verify'] = ssl_details['ca_certs']
            else:
                ssl_args['verify'] = True
            if 'cert_file' in ssl_details and 'key_file' in ssl_details:
                ssl_args['cert'] = [ssl_details['cert_file'],
                                    ssl_details['key_file']]
            elif 'cert_file' in ssl_details:
                ssl_args['cert'] = str(ssl_details['cert_file'])
    return ssl_args


def read_url(url, data=None, timeout=None, retries=0, sec_between=1,
             headers=None, headers_cb=None, ssl_details=None,
             check_status=True, allow_redirects=True, exception_cb=None):
    """Fetch a url (or post to one) with the given options.

    url: url to fetch
    data: any data to POST (this switches the request method to POST
          instead of GET)
    timeout: the timeout (in seconds) to wait for a response
    headers: any headers to provide (and send along) in the request
    headers_cb: called method with single argument of url to get headers
                for request (existence of a header callback overrides
                the usage of a previous headers argument)
    exception_cb: call method with 2 arguments 'request_args' (the
                  arguments used to form the request that failed) and
                  'exception', the exception that occurred
    ssl_details: a dictionary containing any ssl settings, cert_file,
                 ca_certs and verify are valid entries (and they are only
                 used when the url provided is https)
    check_status: checks that the response status is OK after fetching (this
                  ensures a exception is raised on non-OK status codes)
    allow_redirects: enables redirects (or disables them)
    retries: maximum number of retries to attempt when fetching the url and
             the fetch fails
    sec_between: how many seconds to wait between each retry
    """
    url = _clean_url(url)
    req_args = {
        'url': url,
    }
    req_args.update(_get_ssl_args(url, ssl_details))
    req_args['allow_redirects'] = allow_redirects
    req_args['method'] = 'GET'
    if timeout is not None:
        req_args['timeout'] = max(float(timeout), 0)
    if data:
        req_args['method'] = 'POST'
    manual_tries = 1
    if retries:
        manual_tries = max(int(retries) + 1, 1)
    if not headers:
        headers = {
            'User-Agent': 'Cloud-Init/%s' % (version.version_string()),
        }
    if not headers_cb:
        def _cb(url):
            return headers
        headers_cb = _cb
    if data:
        req_args['data'] = data
    if sec_between is None:
        sec_between = -1

    excps = []
    # Handle retrying ourselves since the built-in support
    # doesn't handle sleeping between tries...
    for i in range(0, manual_tries):
        req_args['headers'] = headers_cb(url)
        filtered_req_args = req_args.copy()
        filtered_req_args.pop('data', None)
        try:
            LOG.debug("[%s/%s] open '%s' with %s configuration", i,
                      manual_tries, url, filtered_req_args)
            r = requests.request(**req_args)
            if check_status:
                r.raise_for_status()
            LOG.debug("Read from %s (%s, %sb) after %s attempts", url,
                      r.status_code, len(r.content), (i + 1))
            # Doesn't seem like we can make it use a different
            # subclass for responses, so add our own backward-compat
            # attrs
            return UrlResponse(r)
        except exceptions.RequestException as e:
            if isinstance(e, exceptions.HTTPError):
                excps.append(UrlError(e, code=e.response.status_code,
                                      headers=e.response.headers))
            else:
                excps.append(UrlError(e))
                if SSL_ENABLED and isinstance(e, exceptions.SSLError):
                    # ssl exceptions are not going to get fixed by waiting a
                    # few seconds
                    break
            if exception_cb and not exception_cb(req_args.copy(), excps[-1]):
                break
            if i + 1 < manual_tries and sec_between > 0:
                LOG.debug("Please wait %s seconds while we wait to try again",
                          sec_between)
                time.sleep(sec_between)
    if excps:
        raise excps[-1]
    return None  # Should throw before this...


def wait_for_one_of_urls(urls, max_wait=None, timeout=None,
                         status_cb=None, headers_cb=None, sleep_time=1,
                         exception_cb=None):
    """Wait for one of many urls to respond correctly.

    urls:      a list of urls to try
    max_wait:  roughly the maximum time to wait before giving up
               The max time is *actually* len(urls)*timeout as each url will
               be tried once and given the timeout provided.
               a number <= 0 will always result in only one try
    timeout:   the timeout provided to urlopen
    status_cb: call method with string message when a url is not available
    headers_cb: call method with single argument of url to get headers
                for request.
    exception_cb: call method with 2 arguments 'msg' (per status_cb) and
                  'exception', the exception that occurred.

    The idea of this routine is to wait for the EC2 metdata service to
    come up. On both Eucalyptus and EC2 we have seen the case where
    the instance hit the MD before the MD service was up. EC2 seems
    to have permenantely fixed this, though.

    In openstack, the metadata service might be painfully slow, and
    unable to avoid hitting a timeout of even up to 10 seconds or more
    (LP: #894279) for a simple GET.

    Offset those needs with the need to not hang forever (and block boot)
    on a system where cloud-init is configured to look for EC2 Metadata
    service but is not going to find one.  It is possible that the instance
    data host (169.254.169.254) may be firewalled off Entirely for a sytem,
    meaning that the connection will block forever unless a timeout is set.
    """
    start_time = now()

    def log_status_cb(msg, exc=None):
        LOG.debug(msg)

    if status_cb is None:
        status_cb = log_status_cb

    def timeup(max_wait, start_time):
        return ((max_wait <= 0 or max_wait is None) or
                (now() - start_time > max_wait))

    loop_n = 0
    while True:
        sleep_time = int(loop_n / 5) + 1
        for url in urls:
            _now = now()
            if loop_n != 0:
                if timeup(max_wait, start_time):
                    break
                if timeout and (_now + timeout > (start_time + max_wait)):
                    # shorten timeout to not run way over max_time
                    timeout = int((start_time + max_wait) - _now)

            reason = ""
            url_exc = None
            try:
                if headers_cb is not None:
                    headers = headers_cb(url)
                else:
                    headers = {}

                response = read_url(url, headers=headers, timeout=timeout,
                                    check_status=False)
                if not response.contents:
                    reason = "empty response [%s]" % (response.code)
                    url_exc = UrlError(ValueError(reason), code=response.code,
                                       headers=response.headers)
                elif not response.ok():
                    reason = "bad status code [%s]" % (response.code)
                    url_exc = UrlError(ValueError(reason), code=response.code,
                                       headers=response.headers)
                else:
                    return url
            except UrlError as e:
                reason = "request error [%s]" % e
                url_exc = e
            except Exception as e:
                reason = "unexpected error [%s]" % e
                url_exc = e

            time_taken = int(now() - start_time)
            status_msg = "Calling '%s' failed [%s/%ss]: %s" % (url,
                                                               time_taken,
                                                               max_wait,
                                                               reason)
            status_cb(status_msg)
            if exception_cb:
                # This can be used to alter the headers that will be sent
                # in the future, for example this is what the MAAS datasource
                # does.
                exception_cb(msg=status_msg, exception=url_exc)

        if timeup(max_wait, start_time):
            break

        loop_n = loop_n + 1
        LOG.debug("Please wait %s seconds while we wait to try again",
                  sleep_time)
        time.sleep(sleep_time)

    return False
