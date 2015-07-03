# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

from cloudinit.sources import base as base_source
from cloudinit.sources.openstack import base
from cloudinit import tests
from cloudinit.tests.util import LogSnatcher
from cloudinit.tests.util import mock


class TestBaseOpenStackSource(tests.TestCase):

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '__abstractmethods__', new=())
    def setUp(self):
        self._source = base.BaseOpenStackSource()
        super(TestBaseOpenStackSource, self).setUp()

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_available_versions')
    def _test_working_version(self, mock_available_versions,
                              versions, expected_version):

        mock_available_versions.return_value = versions

        with LogSnatcher('cloudinit.sources.openstack.base') as snatcher:
            version = self._source._working_version()

        msg = "Selected version '{0}' from {1}"
        expected_logging = [msg.format(expected_version, versions)]
        self.assertEqual(expected_logging, snatcher.output)
        self.assertEqual(expected_version, version)

    def test_working_version_latest(self):
        self._test_working_version(versions=(), expected_version='latest')

    def test_working_version_other_version(self):
        versions = (
            base._OS_FOLSOM,
            base._OS_GRIZZLY,
            base._OS_HAVANA,
        )
        self._test_working_version(versions=versions,
                                   expected_version=base._OS_HAVANA)

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_meta_data')
    def test_metadata_capabilities(self, mock_get_meta_data):
        mock_get_meta_data.return_value = {
            'uuid': mock.sentinel.id,
            'hostname': mock.sentinel.hostname,
            'public_keys': {'key-one': 'key-one', 'key-two': 'key-two'},
        }

        instance_id = self._source.instance_id()
        hostname = self._source.host_name()
        public_keys = self._source.public_keys()

        self.assertEqual(mock.sentinel.id, instance_id)
        self.assertEqual(mock.sentinel.hostname, hostname)
        self.assertEqual(["key-one", "key-two"], sorted(public_keys))

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_meta_data')
    def test_no_public_keys(self, mock_get_meta_data):
        mock_get_meta_data.return_value = {'public_keys': []}
        public_keys = self._source.public_keys()
        self.assertEqual([], public_keys)

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_meta_data')
    def test_admin_password(self, mock_get_meta_data):
        mock_get_meta_data.return_value = {
            'meta': {base._ADMIN_PASSWORD: mock.sentinel.password}
        }
        password = self._source.admin_password()
        self.assertEqual(mock.sentinel.password, password)

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_path_join')
    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_cache_data')
    def test_get_content(self, mock_get_cache_data, mock_path_join):
        result = self._source._get_content(mock.sentinel.name)

        mock_path_join.assert_called_once_with(
            'openstack', 'content', mock.sentinel.name)
        mock_get_cache_data.assert_called_once_with(
            mock_path_join.return_value)
        self.assertEqual(mock_get_cache_data.return_value, result)

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_path_join')
    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_cache_data')
    def test_user_data(self, mock_get_cache_data, mock_path_join):
        result = self._source.user_data()

        mock_path_join.assert_called_once_with(
            'openstack', self._source._version, 'user_data')
        mock_get_cache_data.assert_called_once_with(
            mock_path_join.return_value)
        self.assertEqual(mock_get_cache_data.return_value.buffer, result)

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_path_join')
    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_cache_data')
    def test_get_metadata(self, mock_get_cache_data, mock_path_join):
        mock_get_cache_data.return_value = base_source.APIResponse(b"{}")

        result = self._source._get_meta_data()

        mock_path_join.assert_called_once_with(
            'openstack', self._source._version, 'meta_data.json')
        mock_get_cache_data.assert_called_once_with(
            mock_path_join.return_value)
        self.assertEqual({}, result)

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_path_join')
    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_cache_data')
    def test_vendor_data(self, mock_get_cache_data, mock_path_join):
        result = self._source.vendor_data()

        mock_path_join.assert_called_once_with(
            'openstack', self._source._version, 'vendor_data.json')
        mock_get_cache_data.assert_called_once_with(
            mock_path_join.return_value)
        self.assertEqual(mock_get_cache_data.return_value.buffer, result)

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_working_version')
    def test_load(self, mock_working_version):
        self._source.load()

        self.assertTrue(mock_working_version.called)
        self.assertEqual(mock_working_version.return_value,
                         self._source._version)

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_meta_data')
    def test_network_config_no_config(self, mock_get_metadata):
        mock_get_metadata.return_value = {}

        self.assertIsNone(self._source.network_config())

        mock_get_metadata.return_value = {1: 2}

        self.assertIsNone(self._source.network_config())

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_meta_data')
    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_content')
    def test_network_config(self, mock_get_content, mock_get_metadata):
        mock_get_metadata.return_value = {
            "network_config": {base._PAYLOAD_KEY: "content_path"}
        }

        result = self._source.network_config()

        mock_get_content.assert_called_once_with("content_path")
        self.assertEqual(str(mock_get_content.return_value), result)

    @mock.patch('cloudinit.sources.openstack.base.BaseOpenStackSource.'
                '_get_data')
    def test_get_cache_data(self, mock_get_data):
        mock_get_data.return_value = b'test'
        result = self._source._get_cache_data(mock.sentinel.path)

        mock_get_data.assert_called_once_with(mock.sentinel.path)
        self.assertEqual(b'test', result)
