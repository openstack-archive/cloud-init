# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import fixtures
import mock
import os
import textwrap

from cloudinit import templater
from cloudinit.tests import TestCase


class TestTemplates(TestCase):
    jinja_tmpl = '\n'.join((
        "## template:jinja",
        "{{a}},{{b}}",
        ""
    ))
    jinja_params = {'a': '1', 'b': '2'}
    jinja_expected = '1,2\n'

    def test_render_basic(self):
        in_data = textwrap.dedent("""
            ${b}

            c = d
            """)
        in_data = in_data.strip()
        expected_data = textwrap.dedent("""
            2

            c = d
            """)
        out_data = templater.basic_render(in_data, {'b': 2})
        self.assertEqual(expected_data.strip(), out_data)

    def test_render_jinja(self):
        c = templater.render_string(self.jinja_tmpl, self.jinja_params)
        self.assertEqual(self.jinja_expected, c)

    def test_render_jinja_crlf(self):
        blob = '\r\n'.join((
            "## template:jinja",
            "{{a}},{{b}}"))
        c = templater.render_string(blob, {"a": 1, "b": 2})
        self.assertEqual("1,2", c)

    def test_render_default(self):
        blob = '''$a,$b'''
        c = templater.render_string(blob, {"a": 1, "b": 2})
        self.assertEqual("1,2", c)

    def test_render_explict_default(self):
        blob = '\n'.join(('## template: basic', '$a,$b',))
        c = templater.render_string(blob, {"a": 1, "b": 2})
        self.assertEqual("1,2", c)

    def test_render_basic_deeper(self):
        hn = 'myfoohost.yahoo.com'
        expected_data = "h=%s\nc=d\n" % hn
        in_data = "h=$hostname.canonical_name\nc=d\n"
        params = {
            "hostname": {
                "canonical_name": hn,
            },
        }
        out_data = templater.render_string(in_data, params)
        self.assertEqual(expected_data, out_data)

    def test_render_basic_no_parens(self):
        hn = "myfoohost"
        in_data = "h=$hostname\nc=d\n"
        expected_data = "h=%s\nc=d\n" % hn
        out_data = templater.basic_render(in_data, {'hostname': hn})
        self.assertEqual(expected_data, out_data)

    def test_render_basic_parens(self):
        hn = "myfoohost"
        in_data = "h = ${hostname}\nc=d\n"
        expected_data = "h = %s\nc=d\n" % hn
        out_data = templater.basic_render(in_data, {'hostname': hn})
        self.assertEqual(expected_data, out_data)

    def test_render_basic2(self):
        mirror = "mymirror"
        codename = "zany"
        in_data = "deb $mirror $codename-updates main contrib non-free"
        ex_data = "deb %s %s-updates main contrib non-free" % (mirror,
                                                               codename)

        out_data = templater.basic_render(
            in_data, {'mirror': mirror, 'codename': codename})
        self.assertEqual(ex_data, out_data)

    def test_render_basic_exception_1(self):
        in_data = "h=${foo.bar}"
        self.assertRaises(
            TypeError, templater.basic_render, in_data, {'foo': [1, 2]})

    def test_unknown_renderer_raises_exception(self):
        blob = '\n'.join((
            "## template:bigfastcat",
            "Hellow $name"
            ""))
        self.assertRaises(
            ValueError, templater.render_string, blob, {'name': 'foo'})

    @mock.patch.object(templater, 'JINJA_AVAILABLE', False)
    def test_jinja_without_jinja_raises_exception(self):
        blob = '\n'.join((
            "## template:jinja",
            "Hellow {{name}}"
            ""))
        templater.JINJA_AVAILABLE = False
        self.assertRaises(
            ValueError, templater.render_string, blob, {'name': 'foo'})

    def test_render_from_file(self):
        td = self.useFixture(fixtures.TempDir()).path
        fname = os.path.join(td, "myfile")
        with open(fname, "w") as fp:
            fp.write(self.jinja_tmpl)
        rendered = templater.render_from_file(fname, self.jinja_params)
        self.assertEqual(rendered, self.jinja_expected)

    def test_render_to_file(self):
        td = self.useFixture(fixtures.TempDir()).path
        src = os.path.join(td, "src")
        target = os.path.join(td, "target")
        with open(src, "w") as fp:
            fp.write(self.jinja_tmpl)
        templater.render_to_file(src, target, self.jinja_params)
        with open(target, "r") as fp:
            rendered = fp.read()
        self.assertEqual(rendered, self.jinja_expected)
