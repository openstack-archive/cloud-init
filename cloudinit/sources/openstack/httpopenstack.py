# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import contextlib
import logging
import os
import posixpath

import six
from six.moves import http_client
from six.moves.urllib import error
from six.moves.urllib import request

from cloudinit.osys import base as base_osys
from cloudinit.sources import base
from cloudinit.sources.openstack import base as baseopenstack


LOG = logging.getLogger(__name__)


class HttpOpenStackSource(baseopenstack.BaseOpenStackSource):
    """Class for exporting the HTTP OpenStack data source."""

    _POST_PASSWORD_MD_VER = '2013-04-04'

    @staticmethod
    def _enable_metadata_access():
        if os.name == 'nt':
            osutils = base_osys.get_osutils()
            osutils.set_metadata_ip_route(baseopenstack.OPENSTACK_METADATA_URL)

    @staticmethod
    def _path_join(path, *addons):
        return posixpath.normpath(posixpath.join(path, *addons))

    def _available_versions(self):
        version_path = self._path_join(baseopenstack.OPENSTACK_METADATA_URL,
                                       "openstack")
        content = self._get_cache_data(version_path)
        return list(filter(None, content.splitlines()))

    def load(self):
        super(HttpOpenStackSource, self).load()
        self._enable_metadata_access()

        try:
            self._get_meta_data()
            return True
        except Exception:
            LOG.warning('Metadata not found at URL %r',
                        baseopenstack.OPENSTACK_METADATA_URL)
            return False

    @staticmethod
    def _get_response(req):
        try:
            with contextlib.closing(request.urlopen(req)) as handle:
                content = handle.read()
            return content
        except error.HTTPError as exc:
            if exc.code == http_client.NOT_FOUND:
                # No metadata was found, make sure to raise a proper
                # error.
                six.raise_from(base.MissingMetadataError, exc)
            else:
                raise

    def _get_data(self, path):
        norm_path = self._path_join(baseopenstack.OPENSTACK_METADATA_URL, path)
        LOG.debug('Getting metadata from: %s', norm_path)
        req = request.Request(norm_path)
        return self._get_response(req)

    def _post_data(self, path, data):
        norm_path = self._path_join(baseopenstack.OPENSTACK_METADATA_URL, path)
        LOG.debug('Posting metadata to: %s', norm_path)
        req = request.Request(norm_path, data=data)
        self._get_response(req)

    @property
    def _password_path(self):
        return 'openstack/%s/password' % self._version

    @property
    def can_post_password(self):
        """Determine if the password can be posted for the current data source."""
        password = map(int, self._POST_PASSWORD_MD_VER.split("-"))
        if self._version == 'latest':
            current = (0, )
        else:
            current = map(int, self._version.split("-"))
        return tuple(current) > tuple(password)

    @property
    def is_password_set(self):
        path = self._password_path
        return len(self._get_data(path)) > 0

    def post_password(self, password):
        path = self._password_path
        try:
            action = lambda: self._post_data(path, password)
            return self._exec_retry(action)
        except error.HTTPError as ex:
            if ex.code == http_client.CONFLICT:
                # Password already set
                return False
            else:
                raise
