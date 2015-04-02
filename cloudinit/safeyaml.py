# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import yaml


def load(blob):
    """load yaml string return the data represented

    This is basically yaml.safe_load, but explicitly allows the python unicode
    type to be loaded.  This type is allowed for historical purposes as some
    cloud-config producers included it.

    Exception will be raised if types other than the following are found:
        dict, int, float, string, list, python_unicode
    """
    return yaml.safe_load(blob)
