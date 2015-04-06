# Copyright (C) 2015 Canonical Ltd.
# Copyright 2015 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class General(object):
    """Base class for the general namespace.

    This class should contain common functions between all OSes,
    which can't be grouped in a domain-specific namespace.
    """

    def set_timezone(self, timezone):
        """Change the timezone for the underlying platform.

        The `timezone` parameter should be a TZID timezone format,
        e.g. 'Africa/Mogadishu'
        """

    def set_locale(self, locale):
        """Change the locale for the underlying platform."""
