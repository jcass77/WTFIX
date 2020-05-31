# This file is a part of WTFIX.
#
# Copyright (C) 2018-2020 John Cass <john.cass77@gmail.com>
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

import atexit
import logging

from flask import Flask

from wtfix.apps.api.rest import RESTfulServiceApp
from wtfix.conf import settings
from wtfix.pipeline import BasePipeline

app = Flask(__name__)


def get_wsgi_application(*args, session_name=None):
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

    settings.logger = app.logger

    if session_name is None:
        session_name = settings.default_session_name

    app.fix_pipeline = BasePipeline(connection_name=session_name)

    if RESTfulServiceApp.name not in app.fix_pipeline.apps.keys():
        app.logger.warning(
            f"'{RESTfulServiceApp.name}' was not found in the pipeline. It might be unnecessary to run "
            f"WTFIX with a Flask server (unless any of your custom apps also need to serve HTTP requests). "
            f"You should probably use 'run_client.py' instead if you want to use WTFIX as a standalone application."
        )

    atexit.register(
        app.fix_pipeline.stop
    )  # Stop the pipeline when the server is shut down
    app.fix_pipeline.start()

    return app
