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

from wtfix.apps.base import MessageTypeHandlerApp, on
from wtfix.message.admin import TestRequestMessage
from wtfix.protocol.common import MsgType


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


class RESTfulServiceApp(MessageTypeHandlerApp):
    """
    Simple REST interface for communicating with the pipeline.

    Can be used to send messages.
    """

    name = "rest_api_service"

    def __init__(self, pipeline, *args, **kwargs):
        super().__init__(pipeline, *args, **kwargs)

        self.app = None
        self.secret_key = (
            uuid.uuid4().hex
        )  # Secret key used internally by restricted APIs that should only be callable by this app itself.

    @unsync
    async def initialize(self, *args, **kwargs):
        await super().initialize(*args, **kwargs)

        self.app = Flask(__name__)

        api = Api(self.app)
        api.add_resource(Send, "/send", resource_class_args=[self])
        api.add_resource(Shutdown, "/shutdown", resource_class_args=[self])

        self.run_flask()

    @unsync
    def run_flask(self):
        # Start Flask in a separate thread
        self.app.run()

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
