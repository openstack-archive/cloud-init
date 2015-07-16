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
            func = func_namespace['main_' + subcmd.replace("-", "_")]
        sparser = subparsers.add_parser(subcmd, help=val['help'])
        sparser.set_defaults(func=func)
        for (args, kwargs) in val['opts']:
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


COMMON_ARGS = [
    (('--verbose', '-v'), {'action': 'count', 'default': 0}),
]

SUBCOMMANDS = {
    'version': {
        'opts': [],
        'help': 'print cloud-init version',
    },
}


if __name__ == '__main__':
    sys.exit(main())
