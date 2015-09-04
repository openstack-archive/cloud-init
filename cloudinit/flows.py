from taskflow.patterns import graph_flow

from cloudinit import config
from cloudinit import sources


FLOWS = {
    'config': config.get_task_or_flow(),
    'search': sources.get_task_or_flow(),
}


def get_all_flow():
    all_flow = graph_flow.TargetedFlow('all_flow')
    for flow in FLOWS.values():
        all_flow.add(flow)
    return all_flow
