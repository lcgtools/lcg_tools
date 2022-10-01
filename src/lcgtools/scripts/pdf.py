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


"""Creates a printable PDF for a set of card images."""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import os
import os.path
import sys
import textwrap

from lcgtools import LcgException, __version__
from lcgtools.apps.lcgpdf import get_app_properties
from lcgtools.graphics import LcgCardPdfGenerator, LcgAspectRotation, LcgImage
from lcgtools.util import Utility
from PySide6.QtWidgets import QApplication


class Arguments(object):
    """Handles command line argument parsing.

    Parses sysv.args arguments and registers relevant as attributes
    on the :class:`Arguments` object.

    """

    def __init__(self):
        # Set up ArgumentParser for parsing command line arguments
        epilog = """
        Default argument values are shown in [brackets]. If an IMAGE argument
        is a directory, then all files that are images in that directory, are
        included. Bleed is added using a simplistic method, padding the
        outermost pixels of the input image to fill the missing space. By
        default, images with a different (physical) aspect than specified card
        dimensions are rotated to the expected aspect (portrait or landscape).
        In 2-sided mode x and y offsets are applied to the back side pages,
        which enables making adjustments for printer alignment issues.

        """
        epilog = textwrap.dedent(epilog)
        formatter = RawDescriptionHelpFormatter
        parser = ArgumentParser(description='Create PDF file for living card '
                                            'game cards.',
                                formatter_class=formatter, epilog=epilog)
        parser.add_argument('front_files', metavar='IMAGE', nargs='*',
                            help='card front image filename(s) or dir(s)')
        parser.add_argument('-o', '--output', metavar='PDF', nargs=1,
                            type=str, required=True, help='PDF output file')
        parser.add_argument('--overwrite', action='store_true',
                            help='overwrite output file if it already exists')
        parser.add_argument('-l', '--list', metavar='L', action='extend',
                            nargs=1, default=[], type=str, help='card list')
        parser.add_argument('--stdin', action='store_true',
                            help='read card image list(s) from stdin')
        parser.add_argument('--pagesize', nargs=1, type=str.lower,
                            default=[None, ],
                            choices=['a4', 'a3', 'letter', 'tabloid'],
                            help='page size')
        parser.add_argument('--bleed', metavar='MM', nargs=1, type=float,
                            default=[None], help='bleed in mm [a4/a3:3, '
                            'letter/tabloid:1.5]')
        parser.add_argument('--width', metavar='MM', nargs=1, type=float,
                            default=[None], help='card width in mm [61.5]')
        parser.add_argument('--height', metavar='MM', nargs=1, type=float,
                            default=[None], help='card height in mm [88]')
        parser.add_argument('--dpi', nargs=1, type=int, default=[None],
                            help='PDF dpi resolution [600]')
        parser.add_argument('--margin', metavar='MM', nargs=1, type=float,
                            default=[None], help='margin in mm [6]')
        parser.add_argument('--spacing', metavar='MM', nargs=1, type=float,
                            default=[None], help='minimum card spacing in mm '
                            '[a4/a3:1, letter/tabloid:0]')
        parser.add_argument('--fold', metavar='MM', nargs=1, type=float,
                            default=[None], help='card spacing from fold line '
                            'in mm [3]')
        parser.add_argument('--front_bleed', metavar='MM', nargs=1, type=float,
                            default=[None], help='bleed in front image '
                            'file(s) in mm [0]')
        parser.add_argument('-b', '--back', metavar='IMG', nargs=1,
                            type=str, default=[None],
                            help='back image for cards')
        parser.add_argument('--back_bleed', metavar='MM', nargs=1, type=float,
                            default=[None], help='bleed in back image file '
                            'in mm [0]')
        parser.add_argument('--no_rotate', action='store_true',
                            help='disable automatic card rotation')
        parser.add_argument('--rotate_dir', nargs=1, type=str.lower,
                            default=['anticlockwise', ],
                            choices=['clockwise', 'anticlockwise'],
                            help='rotate direction')
        parser.add_argument('--twosided', action='store_true',
                            help='if set print twosided instead of foldable')
        parser.add_argument('--feed_dir', nargs=1, type=str.lower,
                            default=[None],
                            choices=['portrait', 'landscape'],
                            help='print aspect for 2-sided print')
        parser.add_argument('--only_front', action='store_true',
                            help='print only front sides for 2-sided print')
        parser.add_argument('--only_back', action='store_true',
                            help='print only back sides for 2-sided print')
        parser.add_argument('--back_offset_x', metavar='MM', nargs=1,
                            type=float, default=[None],
                            help='back side x offset in mm for 2-sided '
                            'print [0]')
        parser.add_argument('--back_offset_y', metavar='MM', nargs=1,
                            type=float, default=[None],
                            help='back side y offset in mm for 2-sided '
                            'print [0]')
        parser.add_argument('-c', '--conf', action='store_true',
                            help='use the application config file')
        parser.add_argument('-g', '--game', metavar='NAME', nargs=1, type=str,
                            default=[None, ], help='game name (base of .ini '
                            'config file name)')
        parser.add_argument('-p', '--profile', metavar='NAME', nargs=1,
                            type=str, default=[None, ],
                            help='profile in config file for listed cards')
        parser.add_argument('-v', '--verbose', action='store_true',
                            help='enable verbose output to stderr')
        parser.add_argument('--exc', action='store_true',
                            help='show full python exception traces')
        parser.add_argument('--version', action='version',
                            version=f'%(prog)s {__version__}')
        args = parser.parse_args(sys.argv[1:])

        self.front_files = args.front_files
        self.output, = args.output
        self.overwrite = args.overwrite
        self.pagesize, = args.pagesize
        self.bleed, = args.bleed
        self.width, = args.width
        self.height, = args.height
        self.dpi, = args.dpi
        self.margin, = args.margin
        self.spacing, = args.spacing
        self.fold, = args.fold
        self.front_bleed, = args.front_bleed
        self.back_file, = args.back
        self.back_bleed, = args.back_bleed
        self.lists = args.list
        self.parse_stdin = args.stdin
        self.no_rotate = args.no_rotate
        self.rotate_dir, = args.rotate_dir
        self.rotate_dir = self.rotate_dir
        self.twosided = args.twosided
        self.feed_dir, = args.feed_dir
        self.only_front = args.only_front
        self.only_back = args.only_back
        self.back_offset_x, = args.back_offset_x
        self.back_offset_y, = args.back_offset_y
        self.exc = args.exc
        self.conf = args.conf
        self.game, = args.game
        self.profile, = args.profile
        self.verbose = args.verbose

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
        if self.pagesize is None:
            self.pagesize = c_prop('pagesize', profile=profile, default='a4')
        if self.width is None:
            self.width = c_prop('card_width_mm', profile=profile, default=61.5)
        if self.height is None:
            self.height = c_prop('card_height_mm', profile=profile, default=88)
        if self.dpi is None:
            self.dpi = c_prop('page_dpi', profile=profile, default=600)
        if self.margin is None:
            self.margin = c_prop('page_margin_mm', profile=profile, default=6)
        if self.fold is None:
            self.fold = c_prop('card_fold_distance_mm', profile=profile,
                               default=3)
        if self.front_bleed is None:
            self.front_bleed = 0
        if self.bleed is None:
            bleed_def = 3 if self.pagesize in ('a4', 'a3') else 1.5
            self.bleed = c_prop('card_bleed_mm', profile=profile,
                                default=bleed_def)
        if self.spacing is None:
            alt = 1 if self.pagesize in ('a4', 'a3') else 0
            self.spacing = c_prop('card_min_spacing_mm', profile=profile,
                                  default=alt)
        if self.feed_dir is None:
            self.feed_dir = c_prop('feed_dir', profile=profile,
                                   default='portrait')
        self.feed_dir = self.feed_dir.lower()
        if self.back_offset_x is None:
            self.back_offset_x = 0
        if self.back_offset_y is None:
            self.back_offset_y = 0

        # Handle True/False values from config file
        def get_str_bool_prop(prop):
            value_str = c_prop(prop, profile=profile, default='False').lower()
            if value_str == 'false':
                return False
            elif value_str == 'true':
                return True
            else:
                raise LcgException(f'Config file option "{prop}" must be '
                                   f'one of the strings "True" or "False"')
        if not self.twosided:
            self.twosided = get_str_bool_prop('twosided')
        if not self.verbose:
            self.verbose = get_str_bool_prop('verbose')
        if not self.overwrite:
            self.overwrite = get_str_bool_prop('overwrite')

        # Set profile specific defaults
        if self.back_file is None and profile is not None:
            self.back_file = c_prop('backside_image_file', profile=profile,
                                    default=None)
            if self.back_file is not None:
                self.back_file = os.path.expanduser(self.back_file)
        if self.back_bleed is None:
            if profile is not None:
                self.back_bleed = c_prop('backside_bleed_mm', profile=profile,
                                         default=0)
            else:
                self.back_bleed = 0

def main():
    generator = None
    args = None
    try:
        args = Arguments()
        verb = lambda msg: sys.stderr.write(msg+'\n') if args.verbose else None
        if args.conf:
            _conf_file = Utility.path_relative_to_home(args.conf.filename)
            if args.game:
                verb(f'\nLoaded app properties file for game {args.game}:\n'
                     f'{_conf_file}')
            else:
                verb(f'\nLoaded default app properties file:\n'
                     f'{_conf_file}')

        if args.only_front and args.only_back:
            raise LcgException('Cannot apply both of --only_front and '
                               '--only_back')
        odd = False if args.only_back else True
        even = False if args.only_front else True

        # Required to make Qt application run headless
        app = QApplication([sys.argv[0], '-platform', 'offscreen'])

        # Set up a PDF file generator
        if args.overwrite and os.path.exists(args.output):
            os.remove(args.output)
        generator = LcgCardPdfGenerator(outfile=args.output,
                                        pagesize=args.pagesize, dpi=args.dpi,
                                        c_width=args.width,
                                        c_height=args.height,
                                        bleed=args.bleed, margin=args.margin,
                                        spacing=args.spacing, fold=args.fold,
                                        folded=(not args.twosided))
        generator.setTwosidedSubset(odd=odd, even=even)
        generator.setTwosidedEvenPageOffset(args.back_offset_x,
                                            args.back_offset_y)
        generator.setFeedDir(args.feed_dir)

        verb(f'\nOpened {args.output} for PDF output:')
        verb(f'- page size          : {args.pagesize.capitalize()}')
        verb(f'- page margin        : {args.margin:.1f} mm')
        verb(f'- card size          : {args.width:.1f}x{args.height:.1f} mm')
        verb(f'- bleed              : {args.bleed:.1f} mm')
        verb(f'- size with bleed    : {(args.width+2*args.bleed):.1f}x'
             f'{(args.height + 2*args.bleed):.1f} mm')
        verb(f'- card spacing (min) : {args.spacing:.1f} mm')
        verb(f'- max cards per page : {generator.cards_per_page}')

        verb('')
        if not args.twosided:
            verb('Generating folded output format (front & back on same page '
                 'with fold line)')
        else:
            verb('Generating 2-sided output format (fronts and backs on '
                 'separate pages)')
            verb(f'- back side x offset : {args.back_offset_x:.1f} mm')
            verb(f'- back side y offset: {args.back_offset_y:.1f} mm')
            if args.only_front:
                verb('- generating only odd numbered (front side) pages')
            if args.only_back:
                verb('- generating only even numbered (back side) pages')

        # Specify image transform to handle autorotation if specified
        if args.no_rotate:
            aspect_trans = None
        else:
            clockwise = True if args.rotate_dir == 'clockwise' else False
            aspect_trans = LcgAspectRotation(portrait=True,
                                             clockwise=clockwise,
                                             physical=True)

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

        # Add any cards passed on the command line
        if front_files:
            verb('\nProcessing image files passed on command line:')
            if args.back_file is not None:
                back_img = generator.loadCard(args.back_file,
                                              trans=aspect_trans,
                                              bleed=args.back_bleed)
                _back_file = Utility.path_relative_to_home(args.back_file)
                verb(f'- loaded back side ({args.back_bleed:.1f} mm bleed): '
                     f'\n  {_back_file}')
                if not args.twosided:
                    back_img = back_img.rotateHalfCircle()
            else:
                back_img = None
                verb('- using blank back side')
            verb(f'- set bleed on loaded front images to '
                 f'{args.front_bleed:.1f} mm')
            for f in front_files:
                front_img = generator.loadCard(f, trans=aspect_trans,
                                               bleed=args.front_bleed)
                verb(f'- adding card: "{f}"')
                generator.drawCard(front_img, back_img)

        # Parse any list of cards provided on stdin or in provided lists
        lists = args.lists
        if args.parse_stdin:
            lists = [None] + lists
        for l in lists:
            if l is None:
                verb('\nParsing file list from stdin:')
                l = sys.stdin
            else:
                verb(f'\nParsing file list from file "{l}"')
                l = open(l, 'r')
            back_name = None
            back_img = None
            front_bleed = None
            l_num = 0
            for line in l:
                l_num += 1
                line = line.rstrip('\r\n')
                if not line:
                    back_name = None
                    back_img = None
                    front_bleed = None
                else:
                    if back_name is None:
                        # Next line is file name for a card back side
                        back_name = line
                    elif back_img is None:
                        # Next line is bleed mm for provided back side
                        back_bleed = float(line)
                        back_img = generator.loadCard(back_name,
                                                      trans=aspect_trans,
                                                      bleed=back_bleed)
                        _b_name = Utility.path_relative_to_home(back_name)
                        verb(f'- loaded back side ({back_bleed:.1f} mm bleed):'
                             f'\n  {_b_name}')
                        if not args.twosided:
                            back_img = back_img.rotateHalfCircle()
                    elif front_bleed is None:
                        # Next line is the bleed on front images
                        front_bleed = float(line)
                        verb(f'- set bleed on loaded front images to '
                             f'{front_bleed:.1f} mm')
                    else:
                        # Next line is a file name for a card front image
                        _card_file = Utility.path_relative_to_home(line)
                        verb(f'- adding card: {_card_file}')
                        front_img = generator.loadCard(line,
                                                       trans=aspect_trans,
                                                       bleed=front_bleed)
                        generator.drawCard(front_img, back_img)

        # Write PDF file and close
        _out_file = Utility.path_relative_to_home(args.output)
        verb(f'\nCard generation done, saving pdf as {_out_file}\n')
        generator.finish()
    except Exception as e:
        # PDF did not generate successfully, remove PDF file and re-raise
        sys.stderr.write(f'\nError: {e}\n\n')
        if generator:
            generator.abort(remove=True)
        if args and args.exc:
            raise e

if __name__ == '__main__':
    main()
