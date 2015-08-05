# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import contextlib
import os
import shutil
import tempfile

from cloudinit import plugin_finder
from cloudinit.tests import TestCase
from cloudinit.tests import util


class TestPkgutilModuleIterator(TestCase):

    @staticmethod
    @contextlib.contextmanager
    def _create_tmpdir():
        tmpdir = tempfile.mkdtemp()
        try:
            yield tmpdir
        finally:
            shutil.rmtree(tmpdir)

    @contextlib.contextmanager
    def _create_package(self):
        with self._create_tmpdir() as tmpdir:
            path = os.path.join(tmpdir, 'good.py')
            with open(path, 'w') as stream:
                stream.write('name = 42')

            # Make sure this fails.
            bad = os.path.join(tmpdir, 'bad.py')
            with open(bad, 'w') as stream:
                stream.write('import missingmodule')

            yield tmpdir

    def test_pkgutil_module_iterator(self):
        logging_format = ("Could not import the module 'bad' "
                          "using the search path %r")

        with util.LogSnatcher('cloudinit.plugin_finder') as snatcher:
            with self._create_package() as tmpdir:
                expected_logging = logging_format % tmpdir
                iterator = plugin_finder.PkgutilModuleIterator([tmpdir])
                modules = list(iterator.list_modules())

                self.assertEqual(len(modules), 1)
                module = modules[0]
                self.assertEqual(module.name, 42)
                self.assertEqual(len(snatcher.output), 1)
                self.assertEqual(snatcher.output[0], expected_logging)
