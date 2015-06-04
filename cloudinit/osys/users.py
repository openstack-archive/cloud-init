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

from cloudinit import util


@six.add_metaclass(abc.ABCMeta)
class Users(object):
    """Base class for user related operations."""

    @abc.abstractmethod
    def groups(self):
        """Get a list of the groups available in the system."""

    @abc.abstractmethod
    def users(self):
        """Get a list of the users available in the system."""


@six.add_metaclass(abc.ABCMeta)
class Group(object):
    """Base class for user groups."""

    @util.abstractclassmethod
    def create(cls, group_name):
        """Create a new group with the given name."""

    @abc.abstractmethod
    def add(self, member):
        """Add a new member to this group."""


@six.add_metaclass(abc.ABCMeta)
class User(object):
    """Base class for an user."""

    @classmethod
    def create(cls, username, password, **kwargs):
        """Create a new user."""

    @abc.abstractmethod
    def home(self):
        """Get the user's home directory."""

    @abc.abstractmethod
    def ssh_keys(self):
        """Get the ssh keys for this user."""

    @abc.abstractmethod
    def change_password(self, password):
        """Change the password for this user."""
