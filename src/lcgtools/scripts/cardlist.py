#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Cloudberries
#
# This file is part of lcgtools
#
# lcgtools is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# lcgtools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with lcgtools.  If not, see <https://www.gnu.org/licenses/>.
#

"""Creates a card list for lcg_pdf.py standard input."""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import os
import os.path
import sys
import textwrap

from lcgtools import LcgException
from lcgtools.apps.lcgpdf import get_app_properties
from lcgtools.graphics import LcgImage


class Arguments(object):
    """Handles command line argument parsing.

    Parses sysv.args arguments and registers relevant as attributes
    on the :class:`Arguments` object.

    """

    def __init__(self):
        # Parse arguments
        epilog = """
        If an IMAGE argument is a directory, then all files that are images in
        that directory, are included.

        """
        epilog = textwrap.dedent(epilog)
        formatter = RawDescriptionHelpFormatter
        parser = ArgumentParser(description='Creates card list for lcg_pdf.',
                                formatter_class=formatter, epilog=epilog)
        parser.add_argument('front_files', metavar='IMAGE', nargs='+',
                            help='card front image filename(s) or dir(s)')
        parser.add_argument('--front_bleed', metavar='MM', nargs=1, type=float,
                            default=[None], help='bleed in front image '
                            'file(s) in mm [0]')
        parser.add_argument('--back', metavar='BACK_IMG', nargs=1, type=str,
                            default=[None], help='back side image for cards')
        parser.add_argument('--back_bleed', metavar='MM', nargs=1, type=float,
                            default=[None], help='bleed in back image file '
                            'in mm [default 0]')
        parser.add_argument('--output', metavar='FILE', nargs=1, type=str,
                            default=[None], help='write card list to file '
                            '(otherwise stdout)')
        parser.add_argument('--append', action='store_true',
                            help='append to output file')
        parser.add_argument('--stdin', action='store_true',
                            help='pass on card image list(s) from stdin')
        parser.add_argument('--first', action='store_true',
                            help='if set insert before any files from stdin')
        parser.add_argument('--conf', action='store_true',
                            help='use the application config file')
        parser.add_argument('--game', metavar='NAME', nargs=1, type=str,
                            default=[None, ], help='game name (base of .ini '
                            'config file name)')
        parser.add_argument('--profile', metavar='NAME', nargs=1, type=str,
                            default=[None, ], help='profile in config file '
                            'for listed cards')
        parser.add_argument('--verbose', action='store_true',
                            help='enable verbose output to stderr')
        parser.add_argument('--exc', action='store_true',
                            help='show full python exception traces')
        args = parser.parse_args(sys.argv[1:])

        self.front_files = args.front_files
        self.front_bleed, = args.front_bleed
        self.back_file, = args.back
        self.back_bleed, = args.back_bleed
        self.out_file, = args.output
        self.append = args.append
        self.pass_on_stdin = args.stdin
        self.first = args.first
        self.conf = args.conf
        self.game, = args.game
        self.profile, = args.profile
        self.verbose = args.verbose
        self.exc = args.exc

        # If --conf was specified, load config file
        if self.conf:
            self.conf = get_app_properties(game=self.game)
        else:
            self.conf = None

        # Set defaults
        if self.conf:
            c_prop = self.conf.get_property
        else:
            c_prop = lambda prop, profile, default: default
        profile = self.profile
        if self.front_bleed is None:
            self.front_bleed = 0
        if self.back_file is None and profile is not None:
            self.back_file = c_prop('backside_image_file', profile=profile,
                                    default=None)
            if self.back_file is not None:
                self.back_file = os.path.expanduser(self.back_file)
        if self.back_bleed is None:
            if profile is not None:
                self.back_bleed = c_prop('backside_bleed_mm',
                                         profile=profile, default=0)
            else:
                self.back_bleed = 0

        if self.back_file is None:
            raise LcgException('Back side image must be set either as --back '
                               'or in a config file')


# Main program
def main():
    args = None
    try:
        args = Arguments()
        verb = lambda s: sys.stderr.write(s + '\n') if args.verbose else None

        if args.out_file is not None:
            if args.append:
                verb(f'Appending card list to file {args.out_file}')
                out = open(args.out_file, 'a')
            else:
                verb(f'(Over)writing card list to file {args.out_file}')
                out = open(args.out_file, 'w')
        else:
            verb(f'Writing card list to stdout')
            out = sys.stdout

        if args.pass_on_stdin and not args.first:
            verb(f'Pulling file list inputs from stdin to the output')
            for line in sys.stdin:
                out.write(line)

        # Parse front_files arguments and resolve images in directories
        front_files = []
        for f in args.front_files:
            if os.path.isdir(f):
                # For directories, include all image files inside
                for f2 in os.listdir(f):
                    f2 = os.path.join(f, f2)
                    if os.path.isfile(f2):
                        if not LcgImage(f2).isNull():
                            front_files.append(f2)
            else:
                # For files, validate that they are an image file
                if LcgImage(f).isNull():
                    raise LcgException(f'Not a valid image: "{f}"')
                front_files.append(f)

        verb(f'Specifying card back side image       : "{args.back_file}"')
        out.write(f'{args.back_file}\n')
        verb(f'Setting bleed included on back        : {args.back_bleed} mm')
        out.write(f'{args.back_bleed}\n')
        verb(f'Setting bleed included on loaded cards: {args.front_bleed} mm')
        out.write(f'{args.front_bleed}\n')

        for f in front_files:
            verb(f'Adding image: {f}')
            out.write(f'{f}\n')
        out.write('\n')

        if args.pass_on_stdin and args.first:
            verb(f'Pulling file list inputs from stdin to the output')
            for line in sys.stdin:
                out.write(line)

        if args.out_file is not None:
            out.close()
    except Exception as e:
        # Program did not generate successfully
        sys.stderr.write(f'\nError: {e}\n\n')
        if args and args.exc:
            raise e

        
if __name__ == '__main__':
    main()
