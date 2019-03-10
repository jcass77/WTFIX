# WTFIX

The Pythonic Financial Information eXchange (FIX) client for humans.

[![Build status](https://travis-ci.org/jcass77/WTFIX.svg?branch=develop)](https://travis-ci.org/jcass77/WTFIX)
[![Coverage Status](https://coveralls.io/repos/github/jcass77/WTFIX/badge.svg?branch=develop)](https://coveralls.io/github/jcass77/WTFIX?branch=develop)
[![PyPI version shields.io](https://img.shields.io/pypi/v/wtfix.svg)](https://pypi.python.org/pypi/wtfix/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/wtfix.svg)](https://pypi.python.org/pypi/wtfix/)
[![PyPI license](https://img.shields.io/pypi/l/wtfix.svg)](https://pypi.python.org/pypi/wtfix/)
[![Code style:black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://pypi.org/project/black/)


## Project Highlights

- Pure Python3.
- Batteries included - comes with everything that you need to connect to a FIX server and start sending and receiving messages in minutes. Provides default implementations for:
    - Authentication
    - Maintaining a heartbeat
    - Sequence number management and resend requests
- Fast, easy to understand message processing pipeline based on a modern ``async and await`` implementation. 
- Easily extendable architecture - modular 'apps' can be added to the pipeline stack to add new application logic.
   
    ```python
    PIPELINE_APPS = [
        "my_app.apps.SecretAlgoTradingRecipe",     # <-- Your application logic
        "wtfix.apps.api.RESTfulServiceApp",        # REST API for sending messages
        "wtfix.apps.admin.HeartbeatApp",           # Heartbeat monitoring and maintenance
        "wtfix.apps.admin.AuthenticationApp",      # Login / logout handling
        "wtfix.apps.admin.SeqNumManagerApp",       # Message gap detection and filling
        "wtfix.apps.parsers.RawMessageParserApp",  # Message parsing: Logon (A): {BeginString (8):FIX.4.4 | BodyLength (9):99 | MsgType (35):A | MsgSeqNum (34):1 | SenderCompID (49):SENDER | SendingTime (52):20190305-08:45:45.979 | TargetCompID (56):TARGET | EncryptMethod (98):0 | HeartBtInt (108):30 | Username (553):USERNAME | Password (554):PASSWORD | ResetSeqNumFlag (141):Y | CheckSum (10):94}
        "wtfix.apps.utils.LoggingApp",             # Log inbound and outbound messages
        "wtfix.apps.wire.WireCommsApp",            # Raw message encoding / decoding: b'8=FIX.4.4\x019=99\x0135=A\x0134=1\x0149=SENDER\x0152=20190305-08:42:32.793\x0156=TARGET\x0198=0\x01108=30\x01553=USERNAME\x01554=PASSWORD\x01141=Y\x0110=081\x01'
        "wtfix.apps.sessions.ClientSessionApp",    # HTTP session management
    ]
    ```
    
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

- A simple message tag syntax that is human friendly, with various convenience methods for quick access to commonly
used message attributes.

    ```python
    >>> from wtfix.message import admin
    >>> from wtfix.protocol.common import Tag
    
    # Instantiate a new 'Logon' message
    >>> logon_msg = admin.LogonMessage("my_username", "my_password", heartbeat_int=b"30")
  
    # Readable string representation
    str(logon_msg)
    'Logon (A): {MsgType (35):A | EncryptMethod (98):0 | HeartBtInt (108):30 | Username (553):my_username | Password (554):my_password | 10222:345}
    
    # Example of getting the message type
    >>> logon_msg.type
    'A'
  
    # Example of getting the message type name
    >>> logon_msg.name
    'Logon'
  
    # Find the sequence number
    >>> logon_msg.seq_num
    1

    # Various ways for accessing the different fields that make up the message. Fields are just 
    # (tag, value) namedtuples.
    >>> logon_msg[108]  # Using old school tag number
    (108, b"30")
  
    >>> logon_msg[Tag.HeartBtInt]  # Using the tag name as per the FIX specification
    (108, b"30")
  
    >>> logon_msg.HeartBtInt  # Using tag name shortcut
    (108, b"30")
    ```    
- A pragmatic [unicode sandwich](https://nedbatchelder.com/text/unipain.html) based approach to encoding / decoding messages mean that you never need to deal with byte strings...
 
    ```python
    # Duck typing for doing field value comparisons
    >>> logon_msg.HeartBtInt == 30
    True
  
    >>> logon_msg.HeartBtInt == "30"
    True
  
    >>> logon_msg.HeartBtInt == b"30"
    True
    ```
- ...unless you want to:

    ```python
    # Accessing the underlying byte string
    >>> logon_msg.HeartBtInt.value_ref.value
    b'30'
  
    >>> logon_msg.raw
    b'35=A\x0198=0\x01108=30\x01553=my_username\x01554=my_password\x01'
    ```
-   On the fly field conversions to commonly used types:
 
    ```python
    >>> logon_msg.HeartBtInt.as_str
    '30'
    
    >>> logon_msg.HeartBtInt.as_int
    30
    
    >>> logon_msg.PossDupFlag = "Y"
    >>> logon_msg.PossDupFlag.as_bool
    True
    
    >>> logon_msg.PossDupFlag == True
    True
  
    ```
- A very forgiving approach to repeating groups of message tags:
 
    ```python
    from wtfix.message.message import generic_message_factory
  
    # If you provide a group template, then messages are stored in an 'OrderedDict' for fast lookups
    >>> msg = generic_message_factory((Tag.MsgType, MsgType.ExecutionReport), (Tag.NoMiscFees, 2), (Tag.MiscFeeAmt, 10.00), (Tag.MiscFeeType, 2), (Tag.MiscFeeAmt, 20.00), (Tag.MiscFeeType, "A"), group_templates={Tag.NoMiscFees: [Tag.MiscFeeAmt, Tag.MiscFeeType,]})
    >>> msg._fields
    OrderedDict([(35, (35, 8)), (136, [(136, 2)]:[(137, 10.0), (139, 2)], [(137, 20.0), (139, A)])])
  
    # Get 'NoMiscFees' group
    >>> group = msg.get_group(Tag.NoMiscFees)
    >>> str(group)
    '[NoMiscFees (136):2] | [MiscFeeAmt (137):10.0 | MiscFeeType (139):2] | [MiscFeeAmt (137):20.0 | MiscFeeType (139):A]'
   
    # Determine the number of instances in the group
    >>> group.size
    2
  
    # Retrieve the second group instance
    >>> group.instances[1]
    [(137, 20.0), (139, A)]
   
    # Without a pre-defined group template we fall back to using a (slightly slower) list structure for representing message fields internally
    >>> msg = generic_message_factory((Tag.MsgType, MsgType.ExecutionReport), (Tag.NoMiscFees, 2), (Tag.MiscFeeAmt, 10.00), (Tag.MiscFeeType, 2), (Tag.MiscFeeAmt, 20.00), (Tag.MiscFeeType, "A")
    >>> msg_.fields
    [(35, 8), (136, 2), (137, 10.0), (139, 2), (137, 20.0), (139, A)]
  
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
