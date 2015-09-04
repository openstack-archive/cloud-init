# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import argparse
import contextlib
import sys
import uuid

from taskflow import engines
from taskflow.listeners import logging as logging_listener
from taskflow.persistence import backends
from taskflow.persistence import models

from cloudinit import flows
from cloudinit import logging
from cloudinit.version import version_string

TASKFLOW_DB_FILE = '/tmp/taskflow.db'
FLOW_UUID = str(
    uuid.uuid5(uuid.NAMESPACE_URL, 'https://launchpad.net/cloud-init'))


def populate_parser(parser, common, subcommands):
    """Populate an ArgumentParser with data rather than code

    This replaces boilerplate code with boilerplate data when populating a
    :py:class:`argparse.ArgumentParser`

    :param parser:
        the :py:mod:`argparse.ArgumentParser` to populate.

    :param common:
        a :py:func:`list` of tuples.  Each tuple is args and kwargs that are
        passed onto :py:func:`argparse.ArgumentParser.add_argument`

    :param subcommands:
        a :py:func:dict of subcommands to add.
        The key is added as the subcommand name.
        'func' is called to implement the subcommand.
        'help' is set up as the subcommands help message
        entries in 'opts' are passed onto
        :py:func:`argparse.ArgumentParser.add_argument`
    """
    for (args, kwargs) in common:
        parser.add_argument(*args, **kwargs)

    subparsers = parser.add_subparsers()
    for subcmd in sorted(subcommands):
        val = subcommands[subcmd]
        sparser = subparsers.add_parser(subcmd, help=val['help'])
        sparser.set_defaults(func=val['func'], name=subcmd)
        for (args, kwargs) in val.get('opts', {}):
            sparser.add_argument(*args, **kwargs)


def main(args=sys.argv):
    parser = argparse.ArgumentParser(prog='cloud-init')

    populate_parser(parser, COMMON_ARGS, SUBCOMMANDS)
    parsed = parser.parse_args(args[1:])

    if not hasattr(parsed, 'func'):
        parser.error('too few arguments')
    logging.configure_logging(log_to_console=parsed.log_to_console)
    parsed.func(parsed)
    return 0


def main_version(args):
    sys.stdout.write("cloud-init {0}\n".format(version_string()))


def _get_book_and_flow_detail(persistence):
    """Fetch or create the persisted logbook and flow details.

    :param persistence:
        The persistence backend that should be used to fetch the logbook
        and flow details.
    """
    with contextlib.closing(persistence.get_connection()) as conn:
        conn.upgrade()
        for book in conn.get_logbooks():
            if book.name == 'cloud-init':
                flow_detail = book.find(FLOW_UUID)
                break
        else:
            book = models.LogBook('cloud-init')
            flow_detail = models.FlowDetail('all-the-things', FLOW_UUID)
            book.add(flow_detail)
            conn.save_logbook(book)
    return book, flow_detail


def _get_engine_for_flow(flow):
    """Get a compiled engine for the given flow.

    This will use and update state that has been persisted to disk.

    :param flow:
        A taskflow.flow.Flow for which the engine should be compiled.
    """
    persistence = backends.fetch({
        'connection': 'sqlite:///{0}'.format(TASKFLOW_DB_FILE),
    })
    book, flow_detail = _get_book_and_flow_detail(persistence)
    engine = engines.load(
        flow, backend=persistence, flow_detail=flow_detail, book=book)
    engine.compile()
    return engine


def run_flow(flow_name):
    """Take the global flow and get it to the point matching `flow_name`.

    :param flow_name:
        Run until this part of the global flow (as defined in
        cloudinit.flows) is reached.
    """

    def run_flow_command(_):
        flow = flows.get_all_flow()
        if flow_name != 'all':
            flow.set_target(flows.FLOWS[flow_name])

        engine = _get_engine_for_flow(flow)
        with logging_listener.DynamicLoggingListener(engine):
            engine.run()

    return run_flow_command


def unimplemented_subcommand(args):
    raise NotImplementedError(
        "sub command '{0}' is not implemented".format(args.name))


COMMON_ARGS = [
    (('--log-to-console',), {'action': 'store_true', 'default': False}),
    (('--verbose', '-v'), {'action': 'count', 'default': 0}),
]

SUBCOMMANDS = {
    # The stages a normal boot takes
    'network': {
        'func': unimplemented_subcommand,
        'help': 'locate and apply networking configuration',
    },
    'search': {
        'func': run_flow('search'),
        'help': 'search available data sources',
    },
    'config': {
        'func': run_flow('config'),
        'help': 'run available config modules',
    },
    'config-final': {
        'func': unimplemented_subcommand,
        'help': 'run "final" config modules',
    },
    # utility
    'version': {
        'func': main_version,
        'help': 'print cloud-init version',
    },
    'all': {
        'func': run_flow('all'),
        'help': 'run all stages as if from boot',
        'opts': [
            (('--clean',),
             {'help': 'clear any prior system state',
              'action': 'store_true', 'default': False})],
    },
    'clean': {
        'func': unimplemented_subcommand,
        'help': 'clear any prior system state.',
        'opts': [
            (('-F', '--full'),
             {'help': 'be more complete (remove logs).',
              'default': False, 'action': 'store_true'}),
        ],
    },
    'query': {
        'func': unimplemented_subcommand,
        'help': 'query system state',
        'opts': [
            (('--json',),
             {'help': 'output in json format',
              'action': 'store_true', 'default': False})]
    },
}


if __name__ == '__main__':
    sys.exit(main())
