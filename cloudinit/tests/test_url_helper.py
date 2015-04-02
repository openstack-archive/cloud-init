#    Copyright (C) 2015 Yahoo!
#
#    Author: Joshua Harlow <harlowja@yahoo-inc.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 3, as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# vi: ts=4 expandtab

import httpretty

from cloudinit import test
from cloudinit import url_helper


class UrlHelperWaitForUrlsTest(test.TestCase):

    @httpretty.activate
    def test_url_wait_for(self):
        httpretty.HTTPretty.allow_net_connect = False

        urls_actions= [
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
                                           url, body='it worked!')
                else:
                    httpretty.register_uri(httpretty.GET,
                                           url, body='no worky',
                                           status=400)

        url = url_helper.wait_for_one_of_urls(urls)
        self.assertEqual("http://www.yahoo.com", url)

    @httpretty.activate
    def test_url_wait_for_no_work(self):
        httpretty.HTTPretty.allow_net_connect = False

        def request_callback(request, uri, headers):
            return (400, headers, "no worky")

        urls = [
            "http://www.yahoo.com",
            "http://www.google.com",
        ]
        for url in urls:
            httpretty.register_uri(httpretty.GET,
                                   url, body=request_callback)

        self.assertFalse(url_helper.wait_for_one_of_urls(urls, max_wait=1))


class UrlHelperFetchTest(test.TestCase):

    @httpretty.activate
    def test_url_fetch(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.yahoo.com",
                               body='it worked!')

        resp = url_helper.read_url("http://www.yahoo.com")
        self.assertEqual("it worked!", resp.contents)

    @httpretty.activate
    def test_retry_url_fetch(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.yahoo.com",
                               responses=[
                                httpretty.Response(body="no worky",
                                                   status=400),
                                httpretty.Response(body="it worked!",
                                                   status=200),
                               ])

        resp = url_helper.read_url("http://www.yahoo.com",
                                   retries=2, sec_between=0.01)
        self.assertEqual("it worked!", resp.contents)

    @httpretty.activate
    def test_failed_url_fetch(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.yahoo.com",
                               body='no worky', status=400)
        self.assertRaises(url_helper.UrlError,
                          url_helper.read_url, "http://www.yahoo.com")


    @httpretty.activate
    def test_failed_retry_url_fetch(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.yahoo.com",
                               responses=[
                                httpretty.Response(body="no worky",
                                                   status=400),
                                httpretty.Response(body="no worky",
                                                   status=400),
                                httpretty.Response(body="no worky",
                                                   status=400),
                               ])

        self.assertRaises(url_helper.UrlError,
                          url_helper.read_url, "http://www.yahoo.com",
                          retries=2, sec_between=0.01)
