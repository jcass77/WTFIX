# This file is a part of WTFIX.
#
# Copyright (C) 2018,2019 John Cass <john.cass77@gmail.com>
#
# WTFIX is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# WTFIX is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Settings and configuration for wtfix.

Read values from the module specified by the WTFIX_SETTINGS_MODULE environment variable
"""

import importlib
import os
import logging

from . import global_settings
from ..core.exceptions import ImproperlyConfigured

from dotenv import load_dotenv

from pathlib import Path  # python3 only

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

ENVIRONMENT_VARIABLE = "WTFIX_SETTINGS_MODULE"

logger = logging.getLogger("wtfix")


class Settings:
    def __init__(self, settings_module=None):

        if settings_module is None:
            settings_module = os.environ.get(ENVIRONMENT_VARIABLE)

            if not settings_module:
                raise ImproperlyConfigured(
                    f"Settings are not configured. You must either define the environment variable "
                    f"{ENVIRONMENT_VARIABLE} or call settings.configure() before accessing settings."
                )
        # update this dict from global settings (but only for ALL_CAPS settings)
        for setting in dir(global_settings):
            if setting.isupper():
                setattr(self, setting, getattr(global_settings, setting))

        # store the settings module in case someone later cares
        self.WTFIX_SETTINGS_MODULE = settings_module

        mod = importlib.import_module(self.WTFIX_SETTINGS_MODULE)

        tuple_settings = "PIPELINE_APPS"
        self._explicit_settings = set()

        for setting in dir(mod):
            if setting.isupper():
                setting_value = getattr(mod, setting)

                if setting in tuple_settings and not isinstance(
                    setting_value, (list, tuple)
                ):
                    raise ImproperlyConfigured(
                        f"The {setting} setting must be a list or a tuple. "
                    )
                setattr(self, setting, setting_value)
                self._explicit_settings.add(setting)

    def __repr__(self):
        return '<%(cls)s "%(settings_module)s">' % {
            "cls": self.__class__.__name__,
            "settings_module": self.WTFIX_SETTINGS_MODULE,
        }


settings = Settings()
