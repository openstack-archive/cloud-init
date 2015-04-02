# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import httpretty
import shutil
import testtools
import tempfile


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


class TempDir(object):
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp()

    def __enter__(self):
        return self.tmpdir

    def __exit__(self, excp_type, excp_value, excp_traceback):
        return shutil.rmtree(self.tmpdir)
