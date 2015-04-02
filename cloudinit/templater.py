# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import collections
import logging
import os
import re

try:
    import jinja2
    from jinja2 import Template as JTemplate
    JINJA_AVAILABLE = True
except (ImportError, AttributeError):
    JINJA_AVAILABLE = False  # noqa

LOG = logging.getLogger(__name__)
TYPE_MATCHER = re.compile(r"##\s*template:(.*)", re.I)
BASIC_MATCHER = re.compile(r'\$\{([A-Za-z0-9_.]+)\}|\$([A-Za-z0-9_.]+)')


def basic_render(content, params):
    """This does simple replacement of bash variable like templates.

    It identifies patterns like ${a} or $a and can also identify patterns like
    ${a.b} or $a.b which will look for a key 'b' in the dictionary rooted
    by key 'a'.
    """

    def replacer(match):
        # Only 1 of the 2 groups will actually have a valid entry.
        name = match.group(1) or match.group(2)
        if name is None:
            # not sure how this can possibly occur
            raise RuntimeError("Match encountered but no valid group present")
        path = collections.deque(name.split("."))
        selected_params = params
        while len(path) > 1:
            key = path.popleft()
            if not isinstance(selected_params, dict):
                raise TypeError(
                    "Can not traverse into non-dictionary '%s' of type %s "
                    "while looking for subkey '%s'" %
                    (selected_params, type(selected_params), key))
            selected_params = selected_params[key]
        key = path.popleft()
        if not isinstance(selected_params, dict):
            raise TypeError("Can not extract key '%s' from non-dictionary"
                            " '%s' of type %s"
                            % (key, selected_params, type(selected_params)))
        return str(selected_params[key])

    return BASIC_MATCHER.sub(replacer, content)


def detect_template(text):

    def jinja_render(content, params):
        # keep_trailing_newline is in jinja2 2.7+, not 2.6
        add = "\n" if content.endswith("\n") else ""
        return JTemplate(content,
                         undefined=jinja2.StrictUndefined,
                         trim_blocks=True).render(**params) + add

    if "\n" in text:
        ident, rest = text.split("\n", 1)
    else:
        ident = text
        rest = ''
    type_match = TYPE_MATCHER.match(ident)
    if not type_match:
        return ('basic', basic_render, text)
    else:
        template_type = type_match.group(1).lower().strip()
        if template_type not in ('jinja', 'basic'):
            raise ValueError("Unknown template rendering type '%s' requested"
                             % template_type)
        if template_type == 'jinja' and not JINJA_AVAILABLE:
            raise ValueError("Template requested jinja as renderer, but Jinja "
                             "is not available.")
        elif template_type == 'jinja' and JINJA_AVAILABLE:
            return ('jinja', jinja_render, rest)
        # Only thing left over is the basic renderer (it is always available).
        return ('basic', basic_render, rest)


def render_from_file(fn, params, encoding='utf-8'):
    with open(fn, 'rb') as fh:
        content = fh.read()
    content = content.decode(encoding)
    _, renderer, content = detect_template(content)
    return renderer(content, params)


def render_to_file(fn, outfn, params, mode=0o644, encoding='utf-8'):
    contents = render_from_file(fn, params, encoding=encoding)
    with open(outfn, 'wb') as fh:
        fh.write(contents.encode(encoding))
    os.chmod(outfn, mode)


def render_string(content, params):
    _, renderer, content = detect_template(content)
    return renderer(content, params)
