# Copyright (C) 2015 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# vi: ts=4 expandtab

import yaml


class _CustomSafeLoader(yaml.SafeLoader):
    def construct_python_unicode(self, node):
        return self.construct_scalar(node)

_CustomSafeLoader.add_constructor(
    u'tag:yaml.org,2002:python/unicode',
    _CustomSafeLoader.construct_python_unicode)


def load(blob):
    return yaml.load(blob, Loader=_CustomSafeLoader)
