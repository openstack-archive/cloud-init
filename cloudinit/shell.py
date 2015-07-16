# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import argparse
import sys


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

    parsed.func(parsed)
    return 0


def main_version(args):
    sys.stdout.write("cloud-init 1.9\n")
    return


def unimplemented_subcommand(args):
    raise NotImplementedError(
        "sub command '{0}' is not implemented".format(args.name))


COMMON_ARGS = [
    (('--verbose', '-v'), {'action': 'count', 'default': 0}),
]

SUBCOMMANDS = {
    # The stages a normal boot takes
    'network': {
        'func': unimplemented_subcommand,
        'help': 'locate and apply networking configuration',
    },
    'search': {
        'func': unimplemented_subcommand,
        'help': 'search available data sources',
    },
    'config': {
        'func': unimplemented_subcommand,
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
        'func': unimplemented_subcommand,
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
