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

"""Utility functionality."""

import configparser
import os
import os.path
import platform
import tempfile

from lcgtools import LcgException

__all__ = ['LcgAppResources', 'LcgConfigFile', 'LcgPropertiesFile',
           'Utility']


class LcgAppResources(object):
    """Identifies location of standard paths for various type of app data.

    :param appname: name of the app (used in app data paths)
    :type  appname: str
    :param  author: name of app author
    :type   author: str
    :param roaming: use roaming folder on Windows (otherwise local)
    :param homedir: if set, overrides path to user home directory
    :type  homedir: str

    """

    def __init__(self, appname, author='NoAuthor', roaming=False,
                 homedir=None):
        pf = platform.system()
        if pf in ('Linux', 'Darwin', 'Windows'):
            self._platform = pf
        else:
            raise LcgException(f'Platform {pf} not supported')
        if homedir is None:
            homedir = os.path.expanduser('~')
        self._home = homedir
        self._appname = appname
        self._author = author
        self._roaming = roaming

    def user_config_dir(self, create=False):
        """User config data directory.

        :param  create: if True create directory if it does not already exist

        """
        pf = self._platform
        subdir = 'lcgtools'
        if pf == 'Linux':
            path = os.path.join(self._home, '.config/', subdir)
        elif pf == 'Darwin':
            path = os.path.join(self._home, 'Library/Application Support/',
                                subdir)
        elif pf == 'Windows':
            _roaming_path = os.path.join('Appdata', 'Roaming')
            _local_path = os.path.join('Appdata', 'Local')
            top = _roaming_path if self._roaming else _local_path
            path = os.path.join(self._home, top, self._author, subdir)
        else:
            raise RuntimeError('Should never happen')
        if create:
            os.makedirs(path, exist_ok=True)
        return path

    def user_config_file(self, filename):
        """Path to config file in user config directory.

        :param filename: name of file in user config directory
        :type  filename: str

        """
        return os.path.join(self.user_config_dir(), filename)

    def user_config_ini(self, prefix=None, create=False):
        """Config file object for an INI config in the user config folder.

        :param prefix: prefix of [prefix].ini filename (if None uses appname)
        :type  prefix: str
        :param create: if True create the INI file if it does not exist
        :return:       config file object
        :rtype:        :class:`LcgConfigFile`

        """
        path = self.user_config_ini_path(prefix=prefix)
        return LcgConfigFile(path, create=create)

    def user_config_ini_path(self, prefix=None):
        """Full path to INI config in the user config folder.

        :param prefix: prefix of [prefix].ini filename (if None uses appname)
        :type  prefix: str
        :return:       full path for config file
        :rtype:        str

        """
        filename = (self._appname if prefix is None else prefix) + '.ini'
        return os.path.join(self.user_config_dir(), filename)

    def user_properties_ini(self, prefix=None, defaults=[], general=[],
                            create=False):
        """Similar to :meth:`user_config_ini` but for a properties file.

        :param   prefix: prefix of [prefix].ini filename (if None uses appname)
        :type    prefix: str
        :param defaults: list of property names allowed in defaults section
        :param  general: list of additional properties allowed in sections
        :param   create: if True create the INI file if it does not exist
        :return:         config file object for specified properties
        :rtype:          class:`LcgPropertiesFile`

        """
        path = self.user_config_ini_path(prefix=prefix)
        return LcgPropertiesFile(path, defaults=defaults, general=general,
                                 create=create)

    def user_data_dir(self, create=False):
        """User config data directory.

        :param  create: if True create directory if it does not already exist

        """
        pf = self._platform
        if pf == 'Linux':
            path = os.path.join(self._home, '.local/share/', self._appname)
        elif pf == 'Darwin':
            path = os.path.join(self._home, 'Library/Application Support/',
                                self._appname)
        elif pf == 'Windows':
            _roaming_path = os.path.join('Appdata', 'Roaming')
            _local_path = os.path.join('Appdata', 'Local')
            top = _roaming_path if self._roaming else _local_path
            path = os.path.join(self._home, top, self._author, self._appname)
        else:
            raise RuntimeError('Should never happen')
        if create:
            os.makedirs(path, exist_ok=True)
        return path


class LcgConfigFile(configparser.ConfigParser):
    """Config file parser for lcgtools INI files.

    :param filename: name of config INI file
    :type  filename: str
    :param   create: if True, create the file if it does not already exist

    """

    def __init__(self, filename, create=False):
        super().__init__(self)
        try:
            result = self.read(filename)
        except Exception as e:
            raise LcgException(f'Invalid INI file {filename}: {e}')
        else:
            if not result:
                if create:
                    # TODO - add any standard config file contents here
                    with open(filename, 'w') as f:
                        self.write(f)
                else:
                    raise LcgException(f'File {filename} does not exist')
            self._filename = filename

    def add_profile(self, name, silent=False):
        """Adds a profile of the given name.

        :param profile: name of profile
        :type  profile: str
        :param  silent: if False raise an exception if profile already exists
        :return:        associated section
        :rtype:         :class:`configparser.SectionProxy`

        """
        if name == self.default_section:
            raise LcgException(f'Illegal profile name: {name}')
        if name not in self:
            self.add_section(name)
        elif not silent:
            raise LcgException(f'Profile already exists: {name}')
        return self[name]

    def profile(self, name, create=False):
        """Gets the profile of the given name.

        :param   name: profile name (must be a legal INI section name)
        :type    name: str
        :param create: if True create profile if it does not already exist
        :return:       associated section
        :rtype:        :class:`configparser.SectionProxy`

        """
        if name == self.default_section:
            raise LcgException(f'Illegal profile name: {name}')
        if name in self:
            return self[name]
        elif create:
            self.add_section(name)
            return self[name]
        else:
            raise LcgException(f'No such profile: {name}')

    def profiles(self):
        """Get a list of :class:`configparser.SectionProxy` sections."""
        return [self[s] for s in self.sections()]

    def profile_names(self):
        """Get a list of registered profile names."""
        return self.sections()

    def remove_profile(self, name, silent=True):
        """Removes the profile of the given name.

        :param profile: name of profile
        :type  profile: str
        :param  silent: if True do not raise exception if profile doesn't exist

        """
        if not self.remove_section(name) and not silent:
            raise LcgException(f'No such profile: {name}')

    def default_profile(self):
        """Returns the default values section.

        :return: associated section
        :rtype:  :class:`configparser.SectionProxy`

        """
        return self[self.default_section]

    def save(self):
        """Saves the config file."""
        tf = tempfile.NamedTemporaryFile(mode='w', delete=False)
        with tf:
            self.write(tf)
            tf.flush()
        try:
            os.replace(tf.name, self._filename)
        except Exception as e:
            os.remove(tf.name)
            raise LcgException(f'Could not replace config file: {e}')

    @property
    def filename(self):
        """Name of the associated config INI file."""
        return self._filename


class LcgPropertiesFile(LcgConfigFile):
    """Config file which restricts keys to a defined set of properties.

    :param filename: name of config INI file
    :type  filename: str
    :param defaults: list of (property name, type) allowed in defaults section
    :param  general: list of additional (property name, type) for sections
    :param   create: if True, create the file if it does not already exist

    """

    def __init__(self, filename, defaults=[], general=[], create=False):
        super().__init__(filename=filename, create=create)
        if 'default' in defaults or 'default' in general:
            raise LcgException('Illegal property name in config '
                               'file: "default"')
        if set(defaults) & set(general):
            raise LcgException('overlapping "defaults" and "general" lists')
        self._properties = dict()
        self._default_properties = dict()
        for prop, _type in defaults:
            self._default_properties[prop] = _type
            self._properties[prop] = _type
        self._general_properties = dict()
        for prop, _type in general:
            self._general_properties[prop] = _type
            self._properties[prop] = _type

    def get_property(self, name, profile=None, default=None):
        """Gets the value of the supported property.

        :param    name: property name
        :type     name: str
        :param profile: name of profile to get property from (default if None)
        :type  profile: str
        :param default: value to return if property is not set
        :return:        property value, or default if not found
        :rtype:         converted to type specified for the property

        If the property is not defined in the specified profile but it is set
        in the default profile, then the default profile's property value
        is returned.

        """
        if name not in self._default_properties:
            if profile is None:
                raise LcgException(f'Not a legal default property: {name}')
            if name not in self._general_properties:
                raise LcgException(f'Not a legal property: {name}')
        if profile is None:
            profile = self.default_profile()
        else:
            profile = self.profile(profile)
        if name not in profile:
            return default
        else:
            _type = self._properties[name]
            value = profile[name]
            try:
                value = _type(value)
            except Exception:
                raise LcgException(f'Could not convert property value '
                                   f'{value} to type {_type}')
            else:
                return value

    def set_property(self, name, value, profile=None):
        """Sets the value of a supported property.

        :type  profile: str
        :param    name: property name
        :type     name: str
        :param   value: property value
        :param profile: name of profile to set property on (default if None)

        """
        if name not in self._default_properties:
            if profile is None:
                raise LcgException(f'Not a legal default property: {name}')
            if name not in self._general_properties:
                raise LcgException(f'Not a legal property: {name}')
        if profile is None:
            profile = self.default_profile()
        else:
            profile = self.profile(profile)
        _type = self._properties[name]
        try:
            _type(value)
        except Exception:
            raise LcgException(f'Cannot convert value {value} to {_type}')
        profile[name] = str(value)

    def del_property(self, name, profile=None):
        """Removes property from profile.

        :param    name: property name
        :type     name: str
        :param profile: name of profile to get property from (default if None)
        :type  profile: str
        :return:        True if property existed in profile and was removed

        """
        if profile is None:
            profile = self.default_section
        return self.remove_option(profile, name)

    def illegal_property_names(self):
        """Generates a list of illegal section/propery pairs set on object.

        :return: dictionary d[section_name] = (property names,) of illegals

        For the default section, None is used as the section name.

        """
        illegal = dict()
        for prop in self.default_profile():
            if prop == 'default':
                # Special value which should be ignored
                continue
            if prop not in self._default_properties:
                if None not in illegal:
                    illegal[None] = []
                illegal[None].append(prop)
        allowed = set(self._default_properties) | set(self._general_properties)
        for prof_name in self.profile_names():
            profile = self.profile(prof_name)
            for prop in profile:
                if prop == 'default':
                    # Special value which should be ignored
                    continue
                if prop not in allowed:
                    if prof_name not in illegal:
                        illegal[prof_name] = []
                    illegal[prof_name].append(prop)
        return illegal

    def validate(self):
        """Validates whether the format of the config file is valid.

        :return: a list of strings describing all problems (empty if valid)

        The method checks property names and type. It does not however check
        whether data is valid, e.g. if file names point to an actual file.

        """
        issues = []
        for prop in self.default_profile():
            if prop == 'default':
                # Special value which should be ignored
                continue
            if prop not in self._default_properties:
                issues.append(f'Illegal default property name: {prop}')
            else:
                try:
                    self.get_property(prop)
                except LcgException:
                    issues.append(f'Default property has wrong type: {prop}')
        allowed = set(self._default_properties) | set(self._general_properties)
        for prof_name in self.profile_names():
            profile = self.profile(prof_name)
            for prop in profile:
                if prop == 'default':
                    # Special value which should be ignored
                    continue
                if prop not in allowed:
                    issues.append(f'Illegal [{prof_name}] property name:'
                                  f' {prop}')
                else:
                    try:
                        self.get_property(prop, profile=prof_name)
                    except LcgException:
                        issues.append(f'[{prof_name}] property has wrong '
                                      f'type: {prop}')
        return issues

    @property
    def default_properties(self):
        """Set of allowed property names for default section."""
        return set(self._default_properties.keys())

    @property
    def properties(self):
        """Set of allowed property names for non-default sections."""
        return set(self._properties.keys())


class Utility(object):
    """Aggregation of various utility function as class methods."""

    @classmethod
    def path_relative_to_home(cls, path, shortest=True):
        """Replaces with path relative to home dir.

        :param     path: path to replace
        :type      path: str
        :param shortest: if True, return path relative to home only if shorter
        :return:         path, possibly modified
        :rtype:          str

        """
        abs_path = os.path.abspath(path)
        home = os.path.expanduser('~')
        if abs_path.startswith(home):
            rel_path = '~' + abs_path[len(home):]
            if os.path.isdir(abs_path) and not rel_path.endswith(os.sep):
                rel_path += os.sep
        else:
            rel_path = None
        if rel_path is None or (shortest and len(rel_path) >= len(path)):
            return path
        else:
            return rel_path
