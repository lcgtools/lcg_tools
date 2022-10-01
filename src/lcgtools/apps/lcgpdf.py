#!/usr/bin/env python3
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

"""Shared code for the lcg_pdf script."""

import os

from lcgtools import LcgException
from lcgtools.util import LcgAppResources

__all__ = ['get_app_properties']


def get_app_properties(game=None, create=False):
    """Gets a properties config object for (a game for) the app.

    :param   game: game name (generic properties if None)
    :type    game: str
    :param create: if True, create config file if it does not exist
    :return:       properties file access object
    :rtype:        :class:`lcgtools.util.LcgPropertiesFile`
    :raises:       :exc:`lcgtools.LcgException`

    If *game* is specified, then the config object will reference a file
    `games/[game].ini` within the lcgtools apps config folder.

    """
    try:
        ar = LcgAppResources(appname='lcg_pdf', author='Cloudberries',)
        app_default_prop = (('pagesize', str),
                            ('page_margin_mm', float),
                            ('feed_dir', str),
                            ('page_dpi', float),
                            ('card_width_mm', float),
                            ('card_height_mm', float),
                            ('card_bleed_mm', float),
                            ('card_min_spacing_mm', float),
                            ('card_fold_distance_mm', float),
                            ('twosided', str),
                            ('verbose', str),
                            ('overwrite', str),
                            ('append', str))
        app_general_prop = (('backside_image_file', str),
                            ('backside_bleed_mm', float))
        if game:
            game = os.path.join('games', game)
        conf = ar.user_properties_ini(prefix=game, defaults=app_default_prop,
                                      general=app_general_prop, create=create)
    except LcgException:
        path = ar.user_config_ini_path(prefix=game)
        raise LcgException(f'Could not load config file "{path}"')
    else:
        issues = conf.validate()
        if issues:
            issues = [f'"{i}"' for i in issues]
            issues_str = ', '.join(issues)
            raise LcgException(f'Invalid config file: {issues_str}')
        else:
            return conf
