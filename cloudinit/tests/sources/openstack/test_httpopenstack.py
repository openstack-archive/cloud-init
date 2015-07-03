# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import textwrap

from six.moves import http_client

from cloudinit import exceptions
from cloudinit.sources import base
from cloudinit.sources.openstack import httpopenstack
from cloudinit import tests
from cloudinit.tests.util import LogSnatcher
from cloudinit.tests.util import mock
from cloudinit import url_helper


class TestHttpOpenStackSource(tests.TestCase):

    def setUp(self):
        self._source = httpopenstack.HttpOpenStackSource()
        super(TestHttpOpenStackSource, self).setUp()

    @mock.patch.object(httpopenstack, 'IS_WINDOWS', new=False)
    @mock.patch('cloudinit.osys.windows.network.Network.'
                'set_metadata_ip_route')
    def test__enable_metadata_access_not_nt(self, mock_set_metadata_ip_route):
        self._source._enable_metadata_access(mock.sentinel.metadata_url)

        self.assertFalse(mock_set_metadata_ip_route.called)

    @mock.patch.object(httpopenstack, 'IS_WINDOWS', new=True)
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
        2013-02-02
        2014-04-04

        2015-05-05

        latest""")
        versions = self._source._available_versions()
        expected = ['2013-02-02', '2014-04-04', '2015-05-05', 'latest']
        mock_get_cache_data.assert_called_once_with("openstack")
        self.assertEqual(expected, versions)

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._get_cache_data')
    def _test__available_versions_invalid_versions(
            self, version, mock_get_cache_data):

        mock_get_cache_data.return_value = version

        exc = self.assertRaises(exceptions.CloudInitError,
                                self._source._available_versions)
        expected = 'Invalid API version %r' % (version,)
        self.assertEqual(expected, str(exc))

    def test__available_versions_invalid_versions(self):
        versions = ['2013-no-worky', '2012', '2012-02',
                    'lates', '20004-111-222', '2004-11-11111',
                    '  2004-11-20']
        for version in versions:
            self._test__available_versions_invalid_versions(version)

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._get_cache_data')
    def test__available_versions_no_version_found(self, mock_get_cache_data):
        mock_get_cache_data.return_value = ''

        exc = self.assertRaises(exceptions.CloudInitError,
                                self._source._available_versions)
        self.assertEqual('No metadata versions were found.', str(exc))

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._get_cache_data')
    def _test_is_password_set(self, mock_get_cache_data, data, expected):
        mock_get_cache_data.return_value = data

        result = self._source.is_password_set
        self.assertEqual(expected, result)
        mock_get_cache_data.assert_called_once_with(
            self._source._password_path)

    def test_is_password_set(self):
        empty_data = base.APIResponse(b"")
        non_empty_data = base.APIResponse(b"password")
        self._test_is_password_set(data=empty_data, expected=False)
        self._test_is_password_set(data=non_empty_data, expected=True)

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

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._path_join')
    @mock.patch('cloudinit.url_helper.wait_any_url')
    def test__get_data_inaccessible_metadata(self, mock_wait_any_url,
                                             mock_path_join):

        mock_wait_any_url.return_value = None
        mock_path_join.return_value = mock.sentinel.path_join
        msg = "Metadata for url {0} was not accessible in due time"
        expected = msg.format(mock.sentinel.path_join)
        expected_logging = [
            'Getting metadata from: %s' % mock.sentinel.path_join
        ]
        with LogSnatcher('cloudinit.sources.openstack.'
                         'httpopenstack') as snatcher:
            exc = self.assertRaises(exceptions.CloudInitError,
                                    self._source._get_data, 'test')

        self.assertEqual(expected, str(exc))
        self.assertEqual(expected_logging, snatcher.output)

    @mock.patch('cloudinit.sources.openstack.httpopenstack.'
                'HttpOpenStackSource._path_join')
    @mock.patch('cloudinit.url_helper.wait_any_url')
    def test__get_data(self, mock_wait_any_url, mock_path_join):
        mock_response = mock.Mock()
        response = b"test"
        mock_response.contents = response
        mock_response.encoding = 'utf-8'

        mock_wait_any_url.return_value = (None, mock_response)
        mock_path_join.return_value = mock.sentinel.path_join
        expected_logging = [
            'Getting metadata from: %s' % mock.sentinel.path_join
        ]
        with LogSnatcher('cloudinit.sources.openstack.'
                         'httpopenstack') as snatcher:
            result = self._source._get_data('test')

        self.assertEqual(expected_logging, snatcher.output)
        self.assertIsInstance(result, base.APIResponse)
        self.assertEqual('test', str(result))
        self.assertEqual(b'test', result.buffer)
