# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab
from taskflow import task


class ConfigTask(task.Task):

    def execute(self, data_source):
        print("Performing configuration using data source: {0}".format(
            data_source))


def get_task_or_flow():
    return ConfigTask()
