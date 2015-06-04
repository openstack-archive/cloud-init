# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import contextlib
import logging
import posixpath

import six
from six.moves.urllib import error
from six.moves.urllib import request

from cloudinit.sources import base
from cloudinit.sources import baseopenstack
from cloudinit.utils import network


LOG = logging.getLogger(__name__)
HTTP_CONFLICT = 409
HTTP_NOT_FOUND = 404


class OpenStackSource(baseopenstack.BaseOpenStackSource):
    """Class for exporting the HTTP OpenStack data source."""

    _POST_PASSWORD_MD_VER = '2013-04-04'

    def load(self):
        super(OpenStackSource, self).load()
        network.set_metadata_ip_route(baseopenstack.OPENSTACK_METADATA_URL)

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
            return content.read()
        except error.HTTPError as exc:
            if exc.code == HTTP_NOT_FOUND:
                # No metadata was found, make sure to raise a proper
                # error.
                six.raise_from(base.MissingMetadataError, exc)
            else:
                raise

    def _get_data(self, path):
        norm_path = posixpath.join(baseopenstack.OPENSTACK_METADATA_URL, path)
        LOG.debug('Getting metadata from: %s', norm_path)
        req = request.Request(norm_path)
        return self._get_response(req)

    def _post_data(self, path, data):
        norm_path = posixpath.join(baseopenstack.OPENSTACK_METADATA_URL, path)
        LOG.debug('Posting metadata to: %s', norm_path)
        req = request.Request(norm_path, data=data)
        self._get_response(req)

    def _get_password_path(self):
        return 'openstack/%s/password' % self._POST_PASSWORD_MD_VER

    @property
    def can_post_password(self):
        try:
            self._get_meta_data(self._POST_PASSWORD_MD_VER)
            return True
        except base.MissingMetadataError:
            return False

    @property
    def is_password_set(self):
        path = self._get_password_path()
        return len(self._get_data(path)) > 0

    def post_password(self, password):
        path = self._get_password_path()
        try:
            action = lambda: self._post_data(path, password)
            return self._exec_retry(action)
        except error.HTTPError as ex:
            if ex.code == HTTP_CONFLICT:
                # Password already set
                return False
            else:
                raise
