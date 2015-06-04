# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import textwrap

from six.moves import http_client

from cloudinit.sources.openstack import httpopenstack
from cloudinit import test
from cloudinit.tests.util import LogSnatcher
from cloudinit.tests.util import mock
from cloudinit import url_helper


class TestHttpOpenStackSource(test.TestCase):

    def setUp(self):
        self._source = httpopenstack.HttpOpenStackSource()
        super(TestHttpOpenStackSource, self).setUp()

    @mock.patch('os.name', new='not nt')
    @mock.patch('cloudinit.osys.windows.network.Network.'
                'set_metadata_ip_route')
    def test__enable_metadata_access_not_nt(self, mock_set_metadata_ip_route):
        self._source._enable_metadata_access(mock.sentinel.metadata_url)

        self.assertFalse(mock_set_metadata_ip_route.called)

    @mock.patch('os.name', new='nt')
    @mock.patch('cloudinit.osys.base.get_osutils')
    def test__enable_metadata_access_nt(self, mock_get_osutils):

        self._source._enable_metadata_access(mock.sentinel.metadata_url)

        mock_get_osutils.assert_called_once_with()
        osutils = mock_get_osutils.return_value
        osutils.network.set_metadata_ip_route.assert_called_once_with(
            mock.sentinel.metadata_url)

    def test__path_join(self):
        calls = [
            (('path', 'a', 'b'), 'path/a/b'),
            (('path', ), 'path'),
            (('path/', 'b/'), 'path/b/'),
        ]
        for arguments, expected in calls:
            path = self._source._path_join(*arguments)
            self.assertEqual(expected, path)

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._get_cache_data')
    def test__available_versions(self, mock_get_cache_data):
        mock_get_cache_data.return_value = textwrap.dedent("""
        first
        second

        third

        fourth""")
        versions = self._source._available_versions()
        mock_get_cache_data.assert_called_once_with("openstack")
        self.assertEqual(["first", "second", "third", "fourth"], versions)

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._get_data')
    def _test_is_password_set(self, mock_get_data, data, expected):
        mock_get_data.return_value = data

        result = self._source.is_password_set
        self.assertEqual(expected, result)
        mock_get_data.assert_called_once_with(self._source._password_path)

    def test_is_password_set(self):
        self._test_is_password_set(data=[], expected=False)
        self._test_is_password_set(data=[1], expected=True)

    def _test_can_update_password(self, version, expected):
        with mock.patch.object(self._source, '_version', new=version):
            self.assertEqual(self._source.can_update_password(), expected)

    def test_can_update_password(self):
        self._test_can_update_password('2012-08-10', expected=False)
        self._test_can_update_password('2012-11-10', expected=False)
        self._test_can_update_password('2013-04-04', expected=True)
        self._test_can_update_password('2014-04-04', expected=True)
        self._test_can_update_password('latest', expected=False)

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._path_join')
    @mock.patch('cloudinit.url_helper.read_url')
    def test__post_data(self, mock_read_url, mock_path_join):
        with LogSnatcher('cloudinit.sources.openstack.'
                         'httpopenstack') as snatcher:
            self._source._post_data(mock.sentinel.path,
                                    mock.sentinel.data)

        expected_logging = [
            'Posting metadata to: %s' % mock_path_join.return_value
        ]
        self.assertEqual(expected_logging, snatcher.output)
        mock_path_join.assert_called_once_with(
            self._source._config['metadata_url'], mock.sentinel.path)
        mock_read_url.assert_called_once_with(
            mock_path_join.return_value, data=mock.sentinel.data,
            retries=self._source._config['retries'],
            timeout=self._source._config['timeout'])

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._post_data')
    def test_post_password(self, mock_post_data):
        self.assertTrue(self._source.post_password(mock.sentinel.password))
        mock_post_data.assert_called_once_with(
            self._source._password_path, mock.sentinel.password)

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._post_data')
    def test_post_password_already_posted(self, mock_post_data):
        exc = url_helper.UrlError(None)
        exc.status_code = http_client.CONFLICT
        mock_post_data.side_effect = exc

        self.assertFalse(self._source.post_password(mock.sentinel.password))
        mock_post_data.assert_called_once_with(
            self._source._password_path, mock.sentinel.password)

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._post_data')
    def test_post_password_other_error(self, mock_post_data):
        exc = url_helper.UrlError(None)
        exc.status_code = http_client.NOT_FOUND
        mock_post_data.side_effect = exc

        self.assertRaises(url_helper.UrlError,
                          self._source.post_password,
                          mock.sentinel.password)
        mock_post_data.assert_called_once_with(
            self._source._password_path, mock.sentinel.password)

    @mock.patch('cloudinit.sources.openstack.base.'
                'BaseOpenStackSource.load')
    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._get_meta_data')
    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._enable_metadata_access')
    def _test_load(self, mock_enable_metadata_access,
                   mock_get_metadata, mock_load, expected,
                   expected_logging, metadata_side_effect=None):

        mock_get_metadata.side_effect = metadata_side_effect
        with LogSnatcher('cloudinit.sources.openstack.'
                         'httpopenstack') as snatcher:
            response = self._source.load()

        self.assertEqual(expected, response)
        mock_enable_metadata_access.assert_called_once_with(
            self._source._config['metadata_url'])
        mock_load.assert_called_once_with()
        mock_get_metadata.assert_called_once_with()
        self.assertEqual(expected_logging, snatcher.output)

    def test_load_works(self):
        self._test_load(expected=True, expected_logging=[])

    def test_load_fails(self):
        expected_logging = [
            'Metadata not found at URL %r'
            % self._source._config['metadata_url']
        ]
        self._test_load(expected=False,
                        expected_logging=expected_logging,
                        metadata_side_effect=ValueError)
