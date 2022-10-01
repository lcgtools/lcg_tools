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

"""Adds (or removes) bleed to an image."""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import os.path
import sys
import textwrap

from lcgtools import LcgException, __version__
from lcgtools.graphics import LcgImage
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
        included. Operations are performed in the following order: rotate,
        resize, add (or crop) bleed. Bleed is added using a simplistic method,
        padding the outermost pixels of the input image to fill the missing
        space. If bleed value is negative then the image is cropped. Exactly
        one of --output or --prefix must be provided. If more than one input
        image is listed, then only --prefix may be used. Only one of the
        options --to_portrait, --to_landscape or --rotate may be used.

        """
        epilog = textwrap.dedent(epilog)
        formatter = RawDescriptionHelpFormatter
        parser = ArgumentParser(description='Make changes to card image(s).',
                                formatter_class=formatter, epilog=epilog)
        parser.add_argument('input', metavar='IMG', nargs='+', type=str,
                            help='source image(s) or dir(s)')
        parser.add_argument('-o', '--output', metavar='IMG', nargs=1,
                            type=str, default=[None],
                            help='output file for single image with bleed')
        parser.add_argument('--prefix', metavar='PREFIX', nargs=1, type=str,
                            default=[None], help='output as prefix+input')
        parser.add_argument('-a', '--rotate_to_aspect', nargs=1,
                            type=str.lower, default=[None, ],
                            choices=['portrait', 'landscape'],
                            help='rotate to target aspect')
        parser.add_argument('--rotate_all', action='store_true',
                            help='performs rotation on all cards')
        parser.add_argument('--rotate_dir', nargs=1, type=str.lower,
                            default=['anticlockwise', ],
                            choices=['clockwise', 'anticlockwise'],
                            help='rotate direction')
        parser.add_argument('-r', '--resize', action='store_true',
                            help='set image size (after rotation, before '
                            'adding bleed)')
        parser.add_argument('-W', '--width', metavar='MM', nargs=1, type=float,
                            default=[61.5, ],
                            help='new (rotated) width in mm [61.5]')
        parser.add_argument('-H', '--height', metavar='MM', nargs=1, type=float,
                            default=[88, ],
                            help='new (rotated) height in mm [88]')
        parser.add_argument('-b', '--bleed', metavar='MM', nargs=1, type=float,
                            default=[0], help='added bleed in mm [0]')
        parser.add_argument('-v', '--verbose', action='store_true',
                            help='enable verbose output to stderr')
        parser.add_argument('--version', action='version',
                            version=f'%(prog)s {__version__}')
        args = parser.parse_args(sys.argv[1:])

        self.inputs = args.input
        self.output, = args.output
        self.prefix, = args.prefix
        self.bleed, = args.bleed
        self.resize = args.resize
        self.width, = args.width
        self.height, = args.height
        self.to_aspect, = args.rotate_to_aspect
        self.rotate = args.rotate_all
        self.rotate_dir, = args.rotate_dir
        self.verbose = args.verbose

        if self.prefix is None and self.output is None:
            raise LcgException('Either prefix or output must be set')
        if self.prefix is not None and self.output is not None:
            raise LcgException('Prefix and output cannot both be set')
        if self.to_aspect is not None and self.rotate:
            raise LcgException('Only one of --rotate_all and '
                               '--rotate_to_aspect may be specified')
        self.to_portrait = (self.to_aspect == 'portrait')
        self.to_landscape = (self.to_aspect == 'landscape')


# Main program
def main():
    # Required to make Qt application run headless
    qapp = QApplication([sys.argv[0], '-platform', 'offscreen'])

    args = Arguments()
    verb = lambda msg: sys.stderr.write(msg + '\n') if args.verbose else None

    # Parse front_files arguments and resolve images in directories
    inputs = []
    for f in args.inputs:
        if os.path.isdir(f):
            # For directories, include all image files inside
            for f2 in os.listdir(f):
                f2 = os.path.join(f, f2)
                if os.path.isfile(f2):
                    if not LcgImage(f2).isNull():
                        inputs.append(f2)
        else:
            # For files, validate that they are an image file
            if LcgImage(f).isNull():
                raise LcgException(f'Not a valid image: "{f}"')
            inputs.append(f)

    if args.output is not None and len(inputs) > 1:
        raise LcgException('--output can only be used with single image')

    for img_name in inputs:
        # Open input image
        _img = Utility.path_relative_to_home(img_name)
        verb(f'Loading image: {_img}')
        img = LcgImage(img_name)
        if img.isNull():
            raise LcgException(f'Could not load as LcgImage: "{img_name}"')

        # Resolve card rotation
        if (args.rotate or
            (args.to_portrait and img.widthMm() > img.heightMm()) or
            (args.to_landscape and img.widthMm() < img.heightMm())):
            if args.rotate_dir == 'clockwise':
                verb('Rotating image clockwise')
                img = img.rotateClockwise()
            else:
                verb('Rotating image anticlockwise')
                img = img.rotateAntiClockwise()

        # Resolve card resizing
        if args.resize:
            verb(f'Resizing image to {args.width}x{args.height} mm')
            img.setWidthMm(args.width)
            img.setHeightMm(args.height)

        # Add (or crop) bleed
        if args.bleed > 0:
            verb(f'Adding {args.bleed} mm bleed')
            img = img.addBleed(args.bleed)
        elif args.bleed < 0:
            verb(f'Cropping {-args.bleed} mm')
            img = img.cropBleed(-args.bleed)

        if args.output is not None:
            out_name = args.output
        else:
            img_dir_path = os.path.dirname(img_name)
            img_filename = os.path.basename(img_name)
            img_filename = args.prefix + img_filename
            out_name = os.path.join(img_dir_path, img_filename)
        _out = Utility.path_relative_to_home(out_name)
        verb(f'Saving result as {_out}\n')
        img.save(out_name)


if __name__ == '__main__':
    main()
