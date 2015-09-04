# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab
from taskflow import task

from cloudinit.plugin_finder import PkgutilModuleIterator
from cloudinit.sources.strategy import SerialSearchStrategy


class GetDataSourceTask(task.Task):
    default_provides = set(['data_source'])

    def execute(self):
        from cloudinit.sources.base import get_data_source
        data_source = get_data_source(
            [], PkgutilModuleIterator, [SerialSearchStrategy])
        return {
            'data_source': data_source.__class__.__name__,
        }


def get_task_or_flow():
    return GetDataSourceTask()
