# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import httpretty

from cloudinit import test
from cloudinit import url_helper


class UrlHelperWaitForUrlsTest(test.TestCase):

    @httpretty.activate
    def test_url_wait_for(self):
        urls_actions = [
            ("http://www.yahoo.com", (False, False, True)),
            ("http://www.google.com", (False, False, False)),
        ]
        urls = []
        for (url, actions) in urls_actions:
            if actions:
                urls.append(url)
            for worked in actions:
                if worked:
                    httpretty.register_uri(httpretty.GET,
                                           url, body=b'it worked!')
                else:
                    httpretty.register_uri(httpretty.GET,
                                           url, body=b'no worky',
                                           status=400)

        url = url_helper.wait_any_url(urls)
        self.assertEqual("http://www.yahoo.com", url)

    @httpretty.activate
    def test_url_wait_for_no_work(self):

        def request_callback(request, uri, headers):
            return (400, headers, b"no worky")

        urls = [
            "http://www.yahoo.com",
            "http://www.google.com",
        ]
        for url in urls:
            httpretty.register_uri(httpretty.GET,
                                   url, body=request_callback)

        self.assertIsNone(url_helper.wait_any_url(urls, max_wait=1))


class UrlHelperFetchTest(test.TestCase):

    @httpretty.activate
    def test_url_fetch(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.yahoo.com",
                               body=b'it worked!')

        resp = url_helper.read_url("http://www.yahoo.com")
        self.assertEqual(b"it worked!", resp.contents)
        self.assertEqual(url_helper.OK, resp.status_code)

    @httpretty.activate
    def test_retry_url_fetch(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.yahoo.com",
                               responses=[
                                   httpretty.Response(body=b"no worky",
                                                      status=400),
                                   httpretty.Response(body=b"it worked!",
                                                      status=200),
                               ])

        resp = url_helper.read_url("http://www.yahoo.com", retries=2)
        self.assertEqual(b"it worked!", resp.contents)
        self.assertEqual(url_helper.OK, resp.status_code)

    @httpretty.activate
    def test_failed_url_fetch(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.yahoo.com",
                               body=b'no worky', status=400)
        self.assertRaises(url_helper.UrlError,
                          url_helper.read_url, "http://www.yahoo.com")

    @httpretty.activate
    def test_failed_retry_url_fetch(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.yahoo.com",
                               responses=[
                                   httpretty.Response(body=b"no worky",
                                                      status=400),
                                   httpretty.Response(body=b"no worky",
                                                      status=400),
                                   httpretty.Response(body=b"no worky",
                                                      status=400),
                               ])

        self.assertRaises(url_helper.UrlError,
                          url_helper.read_url, "http://www.yahoo.com",
                          retries=2)
