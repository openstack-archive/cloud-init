# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import yaml as _yaml

from cloudinit import shell as sh


YAMLError = _yaml.YAMLError


def load(path):
    """Load yaml string from a path and return the data represented.

    Exception will be raised if types other than the following are found:
        dict, int, float, string, list, unicode
    """
    return loads(sh.load_file(path))


def loads(blob):
    """Load yaml string and return the data represented.

    Exception will be raised if types other than the following are found:
        dict, int, float, string, list, unicode
    """
    return _yaml.safe_load(blob)


def dumps(obj):
    """Dumps an object back into a yaml string."""
    formatted = _yaml.safe_dump(obj,
                                line_break="\n",
                                indent=4,
                                explicit_start=True,
                                explicit_end=True,
                                default_flow_style=False)
    return formatted
