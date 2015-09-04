from taskflow import task
from taskflow.patterns import linear_flow

from cloudinit import sources


def get_all_flow():
    all_flow = linear_flow.Flow('all_flow')
    all_flow.add(get_search_flow())
    all_flow.add(get_config_flow())
    return all_flow


def get_config_flow():
    class PlaceHolderTask(task.Task):

        def execute(self, data_source):
            pass

    config_flow = linear_flow.Flow('config_flow')
    config_flow.add(PlaceHolderTask())
    return config_flow


def get_search_flow():
    search_flow = linear_flow.Flow('search_flow')
    search_flow.add(sources.get_task_or_flow())
    return search_flow


FLOWS = {
    'all': get_all_flow(),
    'config': get_config_flow(),
    'search': get_search_flow(),
}
