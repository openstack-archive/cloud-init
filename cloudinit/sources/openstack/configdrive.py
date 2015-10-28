# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import logging
import os
import posixpath
import re
import subprocess
import tempfile

from cloudinit import exceptions
from cloudinit.osys import base
from cloudinit.sources import base as base_source
from cloudinit.sources.openstack import base as base_os


LOG = logging.getLogger(__name__)
IS_WINDOWS = os.name == 'nt'
# Not necessarily the same as using datetime.strftime,
# but should be enough for our use case.
VERSION_REGEX = re.compile('^\d{4}-\d{2}-\d{2}$')
OSUTILS = base.get_osutils()
TMP_DIR = os.path.join(tempfile.gettempdir(), 'config-2')


class ConfigDriveSource(base_os.BaseOpenStackSource):
    """Class for exporting the ConfigDrive data source."""

    datasource_config = {
        'dev_path': '/dev/disk/by-label/config-2',  # linux specific
        'fs_types': ('vfat', 'iso9660'),
    }

    @staticmethod
    def cd_mounter(func):
        """Decorator to handle mounting and umounting."""
        def wrapper(*args, **kwargs):
            subprocess.popen(['mkdir', '-p', TMP_DIR]).communicate()
            for fs in ('vfat', 'iso9660'):
                try:
                    subprocess.check_call(
                        ['mount', '-t', fs, '/dev/disk/by-label/config-2',
                            TMP_DIR])
                except subprocess.CalledProcessError:
                    LOG.debug('ConfigDrive not mounted as %s', fs)
            func(*args, **kwargs)
            subprocess.popen(['umount', TMP_DIR]).communicate()
        return wrapper

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
            msg = 'No configdrive versions were found.'
            raise exceptions.CloudInitError(msg)

        for version in versions:
            if not self._valid_api_version(version):
                msg = 'Invalid ConfigDrive version %r' % (version,)
                raise exceptions.CloudInitError(msg)
        return versions

    @cd_mounter
    def _get_data(self, path):
        norm_path = os.path.join(TMP_DIR, path)
        LOG.debug('Getting metadata from: %s', norm_path)
        if os.path.isfile(norm_path):
            with open(path, 'r') as data:
                cd_data = data.read()
            return base_source.APIResponse(cd_data)
        elif os.path.isdir(norm_path):
            dir_data = '\n'.join(os.listdir(norm_path))
            return base_source.APIResponse(dir_data)

        msg = "Metadata for path {0} was not accessible."
        raise exceptions.CloudInitError(msg.format(norm_path))

    def load(self):
        if IS_WINDOWS:
            # TODO(Any): check config-2 label
            pass
        elif not os.path.exists(self.datasource_config['dev_path']):
            return False

        super(ConfigDriveSource, self).load()

        try:
            self._get_meta_data()
            return True
        except Exception:
            LOG.warning('ConfigDrive with Metadata not found.')
            return False

    @property
    def is_password_set(self):
        return 'admin_pass' in self._get_meta_data()

    @property
    def admin_password(self):
        """Checks is_password_set then returns metadata.admin_pass"""
        if self.is_password_set:
            return self._get_meta_data()['admin_pass']


def data_sources():
    """Get the data sources exported in this module."""
    return (ConfigDriveSource,)
