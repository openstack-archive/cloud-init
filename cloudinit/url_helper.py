# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import logging
import time

try:
    from time import monotonic as now
except ImportError:
    from time import time as now

import requests
from requests import adapters
from requests import exceptions
from requests import structures

# Arg, why does requests vendorize urllib3....
from requests.packages.urllib3 import util as urllib3_util

from six.moves.urllib.parse import quote as urlquote  # noqa
from six.moves.urllib.parse import urlparse  # noqa
from six.moves.urllib.parse import urlunparse  # noqa

from six.moves.http_client import BAD_REQUEST as _BAD_REQUEST
from six.moves.http_client import MULTIPLE_CHOICES as _MULTIPLE_CHOICES
from six.moves.http_client import OK

from cloudinit import version


SSL_ENABLED = True
try:
    import ssl as _ssl  # noqa
except ImportError:
    SSL_ENABLED = False


LOG = logging.getLogger(__name__)


def _get_base_url(url):
    parsed_url = list(urlparse(url, scheme='http'))
    parsed_url[2] = parsed_url[3] = parsed_url[4] = parsed_url[5] = ''
    return urlunparse(parsed_url)


def _clean_url(url):
    parsed_url = list(urlparse(url, scheme='http'))
    if not parsed_url[1] and parsed_url[2]:
        # Swap these since this seems to be a common
        # occurrence when given urls like 'www.google.com'
        parsed_url[1] = parsed_url[2]
        parsed_url[2] = ''
    return urlunparse(parsed_url)


class _Retry(urllib3_util.Retry):
    def is_forced_retry(self, method, status_code):
        # Allow >= 400 to be tried...
        return status_code >= _BAD_REQUEST

    def sleep(self):
        # The base class doesn't have a way to log what we are doing,
        # so replace it with one that does...
        backoff = self.get_backoff_time()
        if backoff <= 0:
            return
        else:
            LOG.debug("Please wait %s seconds while we wait to try again",
                      backoff)
            time.sleep(backoff)


class RequestsResponse(object):
    """A wrapper for requests responses (that provides common functions).

    This exists so that things like StringResponse or FileResponse can
    also exist, but with different sources of there response (aka not
    just from the requests library).
    """

    def __init__(self, response):
        self._response = response

    @property
    def contents(self):
        return self._response.content

    @property
    def url(self):
        return self._response.url

    def ok(self, redirects_ok=False):
        upper = _MULTIPLE_CHOICES
        if redirects_ok:
            upper = _BAD_REQUEST
        return self.status_code >= OK and self.status_code < upper

    @property
    def headers(self):
        return self._response.headers

    @property
    def status_code(self):
        return self._response.status_code

    def __str__(self):
        return self._response.text


class UrlError(IOError):
    def __init__(self, cause, code=None, headers=None):
        super(UrlError, self).__init__(str(cause))
        self.cause = cause
        self.status_code = code
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


def read_url(url, data=None, timeout=None, retries=0,
             headers=None, ssl_details=None,
             check_status=True, allow_redirects=True):
    """Fetch a url (or post to one) with the given options.

    url: url to fetch
    data: any data to POST (this switches the request method to POST
          instead of GET)
    timeout: the timeout (in seconds) to wait for a response
    headers: any headers to provide (and send along) in the request
    ssl_details: a dictionary containing any ssl settings, cert_file,
                 ca_certs and verify are valid entries (and they are only
                 used when the url provided is https)
    check_status: checks that the response status is OK after fetching (this
                  ensures a exception is raised on non-OK status codes)
    allow_redirects: enables redirects (or disables them)
    retries: maximum number of retries to attempt when fetching the url and
             the fetch fails
    """
    url = _clean_url(url)
    request_args = {
        'url': url,
    }
    request_args.update(_get_ssl_args(url, ssl_details))
    request_args['allow_redirects'] = allow_redirects
    request_args['method'] = 'GET'
    if timeout is not None:
        request_args['timeout'] = max(float(timeout), 0)
    if data:
        request_args['method'] = 'POST'
        request_args['data'] = data
    if not headers:
        headers = structures.CaseInsensitiveDict()
    else:
        headers = structures.CaseInsensitiveDict(headers)
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Cloud-Init/%s' % (version.version_string())
    request_args['headers'] = headers
    session = requests.Session()
    if retries:
        retry = _Retry(total=max(int(retries), 0),
                       raise_on_redirect=not allow_redirects)
        session.mount(_get_base_url(url),
                      adapters.HTTPAdapter(max_retries=retry))
    try:
        with session:
            response = session.request(**request_args)
            if check_status:
                response.raise_for_status()
    except exceptions.RequestException as e:
        if e.response is not None:
            raise UrlError(e, code=e.response.status_code,
                           headers=e.response.headers)
        else:
            raise UrlError(e)
    else:
        LOG.debug("Read from %s (%s, %sb)", url, response.status_code,
                  len(response.content))
        return RequestsResponse(response)


def wait_any_url(urls, max_wait=None, timeout=None,
                 status_cb=None, sleep_time=1,
                 exception_cb=None):
    """Wait for one of many urls to respond correctly.

    urls:      a list of urls to try
    max_wait:  roughly the maximum time to wait before giving up
    timeout:   the timeout provided to ``read_url``
    status_cb: call method with string message when a url is not available
    exception_cb: call method with 2 arguments 'msg' (per status_cb) and
                  'exception', the exception that occurred.
    sleep_time: how long to sleep before trying each url again

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

    if not status_cb:
        status_cb = log_status_cb

    def timeup(max_wait, start_time):
        current_time = now()
        return ((max_wait <= 0 or max_wait is None) or
                (current_time - start_time > max_wait))

    loop_n = 0
    while True:
        # This makes a backoff with the following graph:
        #
        # https://www.desmos.com/calculator/c8pwjy6wmt
        sleep_time = int(loop_n / 5) + 1
        for url in urls:
            current_time = now()
            if loop_n != 0:
                if timeup(max_wait, start_time):
                    break
                if (timeout and
                        (current_time + timeout > (start_time + max_wait))):
                    # shorten timeout to not run way over max_time
                    timeout = int((start_time + max_wait) - current_time)
            reason = ""
            url_exc = None
            try:
                response = read_url(url, timeout=timeout, check_status=False)
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

            current_time = now()
            time_taken = int(current_time - start_time)
            status_msg = "Calling '%s' failed [%s/%ss]: %s" % (url,
                                                               time_taken,
                                                               max_wait,
                                                               reason)
            status_cb(status_msg)
            if exception_cb:
                exception_cb(msg=status_msg, exception=url_exc)

        if timeup(max_wait, start_time):
            break

        loop_n = loop_n + 1
        LOG.debug("Please wait %s seconds while we wait to try again",
                  sleep_time)
        time.sleep(sleep_time)

    return None
