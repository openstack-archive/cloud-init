# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import logging
import os
import posixpath
import re

from cloudinit import exceptions
from cloudinit.osys import base
from cloudinit.sources import base as base_source
from cloudinit.sources.openstack import base as baseopenstack
from cloudinit import url_helper


LOG = logging.getLogger(__name__)
IS_WINDOWS = os.name == 'nt'
# Not necessarily the same as using datetime.strftime,
# but should be enough for our use case.
VERSION_REGEX = re.compile('\d{4}-\d{2}-\d{2}')


class HttpOpenStackSource(baseopenstack.BaseOpenStackSource):
    """Class for exporting the HTTP OpenStack data source."""

    datasource_config = {
        'max_wait': 120,
        'timeout': 10,
        'metadata_url': 'http://169.254.169.254/',
        'post_password_version': '2013-04-04',
        'retries': 3,
    }

    @staticmethod
    def _enable_metadata_access(metadata_url):
        if IS_WINDOWS:
            osutils = base.get_osutils()
            osutils.network.set_metadata_ip_route(metadata_url)

    @staticmethod
    def _path_join(path, *addons):
        return posixpath.join(path, *addons)

    @staticmethod
    def _valid_api_version(version):
        if version == 'latest':
            return version
        return VERSION_REGEX.match(version)

    def _available_versions(self):
        content = str(self._get_cache_data("openstack"))
        versions = list(filter(None, content.splitlines()))
        if not versions:
            msg = 'No metadata versions were found.'
            raise exceptions.CloudInitError(msg)

        for version in versions:
            if not self._valid_api_version(version):
                msg = 'Invalid API version {!r}'.format(version)
                raise exceptions.CloudInitError(msg)

        return versions

    def _get_data(self, path):
        norm_path = self._path_join(self._config['metadata_url'], path)
        LOG.debug('Getting metadata from: %s', norm_path)
        response = url_helper.wait_any_url([norm_path],
                                           timeout=self._config['timeout'],
                                           max_wait=self._config['max_wait'])
        if response:
            _, request = response
            return base_source.APIResponse(request.contents,
                                           encoding=request.encoding)

        msg = "Metadata for url {0} was not accessible in due time"
        raise exceptions.CloudInitError(msg.format(norm_path))

    def _post_data(self, path, data):
        norm_path = self._path_join(self._config['metadata_url'], path)
        LOG.debug('Posting metadata to: %s', norm_path)
        url_helper.read_url(norm_path, data=data,
                            retries=self._config['retries'],
                            timeout=self._config['timeout'])

    @property
    def _password_path(self):
        return 'openstack/%s/password' % self._version

    def load(self):
        metadata_url = self._config['metadata_url']
        self._enable_metadata_access(metadata_url)
        super(HttpOpenStackSource, self).load()

        try:
            self._get_meta_data()
            return True
        except Exception:
            LOG.warning('Metadata not found at URL %r', metadata_url)
            return False

    def can_update_password(self):
        """Check if the password can be posted for the current data source."""
        password = map(int, self._config['post_password_version'].split("-"))
        if self._version == 'latest':
            current = (0, )
        else:
            current = map(int, self._version.split("-"))
        return tuple(current) >= tuple(password)

    @property
    def is_password_set(self):
        path = self._password_path
        content = self._get_cache_data(path).buffer
        return len(content) > 0

    def post_password(self, password):
        try:
            self._post_data(self._password_path, password)
            return True
        except url_helper.UrlError as ex:
            if ex.status_code == url_helper.CONFLICT:
                # Password already set
                return False
            else:
                raise
