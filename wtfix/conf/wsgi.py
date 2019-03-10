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

import atexit
from flask import Flask

from unsync import (
    unsync,
)  # Import unsync to set event loop and start ambient unsync thread

from wtfix.conf import settings
from wtfix.pipeline import BasePipeline

app = Flask(__name__)


def get_wsgi_application(session_name=None):
    if session_name is None:
        session_name = settings.default_session_name

    app.fix_pipeline = BasePipeline(session_name=session_name)

    atexit.register(app.fix_pipeline.stop)  # Stop the pipeline when the server is shut down
    app.fix_pipeline.start()

    return app


application = get_wsgi_application()
