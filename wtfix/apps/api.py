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

import base64
import pickle
import uuid

import requests
from flask import Flask, request, abort
from flask_restful import Api, Resource, reqparse
from unsync import unsync

from wtfix.apps.base import BaseApp
from wtfix.conf import settings, logger


class Status(Resource):
    def get(self):
        return "WTFIX REST API is up and running!"


class Send(Resource):
    """
    API endpoint for injecting messages into the pipeline.
    """
    def __init__(self, app):
        self.app = app

        self.parser = reqparse.RequestParser()
        self.parser.add_argument("message", required=True)

    def post(self):
        """
        Endpoint for sending a FIX message.

        'message' should be an instance of FIXMessage that has been pickled and base64 encoded, for example:

            import base64
            import pickle
            import requests

            pickled = pickle.dumps(TestRequestMessage("TEST123"))
            pickled_b64 = base64.b64encode(pickled)

            requests.post("http://localhost:5000/send", data={"message": pickled_b64})

        """
        args = self.parser.parse_args()
        message = pickle.loads(base64.b64decode(args["message"]))

        self.app.send(message)

        return {"sent": f"{message}"}


class Shutdown(Resource):
    """
    Shut down the Flask server (without having to start a dedicated thread outside of the unsync thread pool)
    """
    def __init__(self, app):
        self.app = app

        self.parser = reqparse.RequestParser()
        self.parser.add_argument("token", required=True)

    def post(self):
        args = self.parser.parse_args()

        if args["token"] != self.app.secret_key:
            abort(401, message=f"Invalid token '{args['token']}'.")

        func = request.environ.get("werkzeug.server.shutdown")
        if func is None:
            raise RuntimeError("Not running with the Werkzeug Server")
        func()


class RESTfulServiceApp(BaseApp):
    """
    Simple REST interface for communicating with the pipeline.

    Can be used to send messages.
    """

    name = "rest_api_service"

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

        self._flask_app = None
        self.secret_key = (
            uuid.uuid4().hex
        )  # Secret key used internally by restricted APIs that should only be callable by this app itself.

    @property
    def flask_app(self):
        if self._flask_app is None:

            if settings.FLASK_ENV == "development":
                # We need to start our own Flask application
                logger.info(
                    f"{self.name}: Starting Flask development server..."
                )

                self._flask_app = Flask(__name__)
                self._run_flask_dev_server(self._flask_app)
            else:
                # Must be running as a WSGI application
                from wtfix.conf.wsgi import app

                self._flask_app = app

        return self._flask_app


    @unsync
    async def initialize(self, *args, **kwargs):
        await super().initialize(*args, **kwargs)

        api = Api(self.flask_app)
        api.add_resource(Status, "/")
        api.add_resource(Send, "/send", resource_class_args=[self])
        api.add_resource(Shutdown, "/shutdown", resource_class_args=[self])

    @unsync
    def _run_flask_dev_server(self, flask_app):
        # Start Flask in a separate thread
        flask_app.run()

    # @on(MsgType.Logon)
    # def on_logon(self, message):
    #     pickled = pickle.dumps(TestRequestMessage("TEST123"))
    #     pickled_b64 = base64.b64encode(pickled)
    #
    #     requests.post("http://localhost:5000/send", data={"message": pickled_b64})
    #
    #     return message

    @unsync
    async def stop(self, *args, **kwargs):
        await super().stop(*args, **kwargs)

        requests.post("http://localhost:5000/shutdown", data={"token": self.secret_key})
