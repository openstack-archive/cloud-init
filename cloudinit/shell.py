# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import argparse
import sys


def populate_parser(parser, common, subcommands, func_namespace=None):
    if func_namespace is None:
        func_namespace = globals()

    for (args, kwargs) in common:
        parser.add_argument(*args, **kwargs)

    subparsers = parser.add_subparsers()
    for subcmd in sorted(subcommands.keys()):
        val = subcommands[subcmd]
        func = val.get('func')
        if not func:
            func = func_namespace.get(
                'main_' + subcmd.replace("-", "_"), unimplemented_subcommand)
        sparser = subparsers.add_parser(subcmd, help=val['help'])
        sparser.set_defaults(func=func, name=subcmd)
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
        'help': 'locate and apply networking configuration',
    },
    'search': {
        'help': 'search available data sources',
    },
    'config': {
        'help': 'run available config modules',
    },
    'config-final': {
        'help': 'run "final" config modules',
    },
    # utility
    'version': {
        'help': 'print cloud-init version',
    },
    'all': {
        'opts': [
            (('--clean',),
             {'help': 'clear any prior system state',
              'action': 'store_true', 'default': False}),
         ],
        'help': 'run all stages as if from boot',
    },
    'clean': {
        'help': 'clear any prior system state.',
        'opts': [
            (('-F', '--full'),
             {'help': 'be more complete (remove logs).',
              'default': False, 'action': 'store_true'}),
        ],
    },
    'query': {
       'help': 'query system state',
       'opts': [
           (('--json',),
            {'help': 'output in json format',
             'action': 'store_true', 'default': False}),
       ]
    },
}


if __name__ == '__main__':
    sys.exit(main())
