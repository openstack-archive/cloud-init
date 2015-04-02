# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

from cloudinit import safeyaml
from cloudinit import test

import yaml


class TestSafeYaml(test.TestCase):
    def test_simple(self):
        blob = '\nk1: one\nk2: two'
        expected = {'k1': "one", 'k2': "two"}
        self.assertEqual(safeyaml.load(blob), expected)

    def test_bogus_raises_exception(self):
        badyaml = "1\n 2:"
        self.assertRaises(yaml.error.YAMLError, safeyaml.load, badyaml)

    def test_unsafe_types(self):
        # should not load complex types
        unsafe_yaml = "!!python/object:__builtin__.object {}"
        self.assertRaises(yaml.error.YAMLError, safeyaml.load, unsafe_yaml)

    def test_python_unicode_not_allowed(self):
        # python/unicode is not allowed
        # in the past this type was allowed, but not now, so explicit test.
        blob = "{k1: !!python/unicode 'my unicode', k2: my string}"
        self.assertRaises(yaml.error.YAMLError, safeyaml.load, blob)
