# WTFIX

The Pythonic Financial Information eXchange (FIX) client for humans.

[![Build status](https://travis-ci.org/jcass77/WTFIX.svg?branch=develop)](https://travis-ci.org/jcass77/WTFIX)
[![Coverage Status](https://coveralls.io/repos/github/jcass77/WTFIX/badge.svg?branch=develop)](https://coveralls.io/github/jcass77/WTFIX?branch=develop)
[![PyPI version shields.io](https://img.shields.io/pypi/v/wtfix.svg)](https://pypi.python.org/pypi/wtfix/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/wtfix.svg)](https://pypi.python.org/pypi/wtfix/)
[![PyPI license](https://img.shields.io/pypi/l/wtfix.svg)](https://pypi.python.org/pypi/wtfix/)
[![Code style:black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://pypi.org/project/black/)


## Project Highlights and Goals

- Built from the ground up for Python 3.
- Batteries included - comes with everything that you need to connect to a FIX server and start sending and receiving
messages in minutes. Provides default implementations for:
    - Authentication
    - Maintaining a heartbeat
    - Sequence number management and resend requests
    - Message storage and retrieval
- Fast, easy to understand message processing pipeline based on a modern ``async and await`` implementation.
- Easily extendable architecture - modular 'apps' can be added to the pipeline stack to add custom message processing
routines or new application features.

    ```python
    PIPELINE_APPS = [
        "my_app.apps.SecretAlgoTradingRecipe",     # <-- Your application logic
        "wtfix.apps.api.RESTfulServiceApp",        # REST API for sending messages
        "wtfix.apps.brokers.RedisPubSubApp",       # Redis Pub/Sub broker for sending / receiving messages
        "wtfix.apps.admin.HeartbeatApp",           # Heartbeat monitoring and maintenance
        "wtfix.apps.admin.AuthenticationApp",      # Login / logout handling
        "wtfix.apps.admin.SeqNumManagerApp",       # Message gap detection and filling
        "wtfix.apps.store.MessageStoreApp",        # Store messages (caching or persistence)
        "wtfix.apps.utils.InboundLoggingApp",      # Log inbound messages
        "wtfix.apps.parsers.RawMessageParserApp",  # Message parsing: Logon (A): {BeginString (8): FIX.4.4 | BodyLength (9): 99 | MsgType (35): A | MsgSeqNum (34): 1 | SenderCompID (49): SENDER | SendingTime (52): 20190305-08:45:45.979 | TargetCompID (56): TARGET | EncryptMethod (98): 0 | HeartBtInt (108): 30 | Username (553): USERNAME | Password (554): PASSWORD | ResetSeqNumFlag (141): Y | CheckSum (10): 94}
        "wtfix.apps.utils.OutboundLoggingApp",     # Log outbound messages
        "wtfix.apps.wire.WireCommsApp",            # Raw message encoding / decoding: b'8=FIX.4.4\x019=99\x0135=A\x0134=1\x0149=SENDER\x0152=20190305-08:42:32.793\x0156=TARGET\x0198=0\x01108=30\x01553=USERNAME\x01554=PASSWORD\x01141=Y\x0110=081\x01'
        "wtfix.apps.sessions.ClientSessionApp",    # HTTP session management
    ]
    ```
- Messages can be cached in memory or saved to a Redis message store for later retrieval. Alternatively you can add
your own message storage solution using the provided interfaces.
- Send messages directly from the pipeline, via 3rd party applications using a REST API, or by publishing them to
a Redis Pub/Sub channel for immediate delivery.

- Provides a convenient ``@on`` decorator for fine-grained control over which apps will respond to which types of messages:

    ```python
    from wtfix.apps.base import MessageTypeHandlerApp, on
    from wtfix.protocol.common import MsgType
    from wtfix.conf import settings

    logger = settings.logger

    class SecretAlgoTradingRecipe(MessageTypeHandlerApp):

        @on(MsgType.Logon)  # Only invoked when 'Logon (type A)' messages are received.
        def on_logon(self, message):
            self.send_security_definition_request()
            return message

        def on_receive(self, message):  # Invoked for every type of message.
          logger.info(f"Received message {message}!")
    ```

- Provides custom `Field` and `FieldMap` types for working with FIX tags and field values. These types are 'pythonic',
implementing many of the standard protocols, and behave as expected when you integrate them in existing Python
code.
- A simple message tag syntax, with various convenience methods, for quick access to commonly
used message attributes.

    ```python
    >>> from wtfix.message import admin
    >>> from wtfix.protocol.common import Tag

    # Instantiate a new 'Logon' message
    >>> logon_msg = admin.LogonMessage("my_username", "my_password", heartbeat_int=30)

    # Short, concise string representation
    >>> str(logon_msg)
    'A: {(35, A) | (98, 0) | (108, 30) | (553, my_username) | (554, my_password)}'

    # Pretty print tag names by using the 't' formatting option
    >>> f"{logon_msg:t}"
    'Logon (A): {MsgType (35): A | EncryptMethod (98): 0 | HeartBtInt (108): 30 | Username (553): my_username | Password (554): my_password}'

    # Example of getting the message type
    >>> logon_msg.type
    'A'

    # Example of getting the message type name
    >>> logon_msg.name
    'Logon'

    # Look up the sequence number
    >>> logon_msg.seq_num
    1

    # Various ways for accessing the different fields that make up the message. Fields are just
    # (tag, value) namedtuples.
    >>> logon_msg[108]  # Using old school tag number
    Field(108, '30')

    >>> logon_msg[Tag.HeartBtInt]  # Using the tag name as per the FIX specification
    Field(108, '30')

    >>> logon_msg.HeartBtInt  # Using tag name shortcut
    Field(108, '30')
    ```
- A pragmatic [unicode sandwich](https://nedbatchelder.com/text/unipain.html) based approach to encoding / decoding
messages mean that you never need to deal with byte sequences directly.

    ```python
    from wtfix.message.field import Field
    from wtfix.message.message import generic_message_factory

    # Create a new Message from a byte sequence received over the wire
    >>> fields = Field.fields_frombytes(b"35=A\x0198=0\x01108=30\x01553=my_username\x01554=my_password\x01")
    >>> logon_msg = generic_message_factory(*fields)
    >>> str(logon_msg)
    'A: {(35, A) | (98, 0) | (108, 30) | (553, my_username) | (554, my_password)}'

    # Fields are tuples of (tag, value) pairs
    >>> username = logon_msg.Username

    >>> username.tag
    553

    >>> username.value
    "my_username"

    # Fields behave just like Python's built-in types, and most operations can be performed directly
    # on a field's 'value' attribute.
    >>> username += "_123"
    >>> username
    Field(553, 'my_username_123')
    ```
- Access to the underlying byte sequence when you need it:

    ```python
    >>> bytes(logon_msg)
    b'35=A\x0198=0\x01108=30\x01553=my_username\x01554=my_password\x01'
    ```
-  It is easy to add Fields to a Message: simply assign the tag value:

    ```python
    >>> logon_msg.PossDupFlag = "Y"
    >>> f"{logon_msg:t}"
    'Logon (A): {MsgType (35): A | EncryptMethod (98): 0 | HeartBtInt (108): 30 | Username (553): my_username | Password (554): my_password | PossDupFlag (43): Y}'

    # Most FIX field values can be cast to their corresponding Python built-in type
    >>> bool(logon_msg.PossDupFlag) is True
    True

    ```
- A very forgiving approach to repeating groups of message tags:

    ```python
    from wtfix.protocol.common import Tag, MsgType
    from wtfix.message.message import generic_message_factory

    # If you provide a group template, then messages are stored in an 'OrderedDict' for fast lookups
    >>> msg = generic_message_factory((Tag.MsgType, MsgType.ExecutionReport), (Tag.NoMiscFees, 2), (Tag.MiscFeeAmt, 10.00), (Tag.MiscFeeType, 2), (Tag.MiscFeeAmt, 20.00), (Tag.MiscFeeType, "A"), group_templates={Tag.NoMiscFees: [Tag.MiscFeeAmt, Tag.MiscFeeType,]})
    >>> msg.data
    OrderedDict([(35, Field(35, '8')), (136, Group(Field(136, '2'), Field(137, '10.0'), Field(139, '2'), Field(137, '20.0'), Field(139, 'A')))])

    # Get 'NoMiscFees' group
    >>> group = msg.NoMiscFees
    >>> f"{group:t}"
    '[NoMiscFees (136): 2] | [MiscFeeAmt (137): 10.0 | MiscFeeType (139): 2] | [MiscFeeAmt (137): 20.0 | MiscFeeType (139): A]'

    # Determine the number of instances in the group
    >>> group.size
    2

    # Retrieve the second group instance
    >>> group.instances[1]
    FieldList(Field(137, '20.0'), Field(139, 'A'))

    # Without a pre-defined group template, WTFIX falls back to using a (slightly slower) list structure for representing message fields internally
    >>> msg = generic_message_factory((Tag.MsgType, MsgType.ExecutionReport), (Tag.NoMiscFees, 2), (Tag.MiscFeeAmt, 10.00), (Tag.MiscFeeType, 2), (Tag.MiscFeeAmt, 20.00), (Tag.MiscFeeType, "A"))
    >>> msg.data
    [Field(35, '8'), Field(136, '2'), Field(137, '10.0'), Field(139, '2'), Field(137, '20.0'), Field(139, 'A')]

    ```

## Getting Started

- Install the project's dependencies (e.g. `pip install -r requirements/local.txt`), preferably in a Python virtual
  environment that has been created specifically for that purpose.
- Run the test suite with `pytest` to verify the installation.
- Create a `.env` file in the project's root directory that contains at least the following configuration settings:

    ```python
    # Supports different configuration settings for local development, staging, or production environments.
    WTFIX_SETTINGS_MODULE=config.settings.local

    HOST=             # Required. The FIX server hostname or IP address
    PORT=             # Required. The port on the FIX server to connect to

    SENDER=           # Required. SENDER_COMP_ID (tag 49).
    TARGETD=          # Required. TARGET_COMP_ID (tag 56).

    USERNAME=         # Required. Username to use for Logon messages (tag 553).
    PASSWORD=         # Required. Password to use for logon messages (tag 554).

    PYTHONASYNCIODEBUG=0  # Set to '1' for detailed debugging messages.
    ```

- Start the FIX client with `python runclient.py`. The default implementation will log in to the FIX server and maintain a steady heartbeat.
- Use `Ctrl-C` to quit. This will trigger a `Logout` message to be sent before the pipeline is terminated.

## Project Resources

- [Deploying](docs/deploying.md)
- [Changelog](docs/changelog.md)
- [Release procedures](docs/releasing.md)

## Inspired By

- [slowbreak](https://pypi.org/project/slowbreak/)'s message processing pipeline and ``@on`` decorator
- [simplefix](https://github.com/da4089/simplefix)'s approach to raw message parsing
