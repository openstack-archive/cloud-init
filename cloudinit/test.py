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
import testtools


class TestCase(testtools.TestCase):
    """Base class for all cloud-init test cases."""

    def setUp(self):
        super(TestCase, self).setUp()
        # Do not allow any unknown network connections to get triggered...
        httpretty.HTTPretty.allow_net_connect = False

    def tearDown(self):
        super(TestCase, self).tearDown()
        # Ok allow it again....
        httpretty.HTTPretty.allow_net_connect = True
