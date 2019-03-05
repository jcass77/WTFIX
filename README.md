# WTFIX

The Pythonic Financial Information eXchange client for humans.


## Project Highlights

- Pure Python3.
- Batteries included - everything you need to connect to a FIX server and start sending and receiving messages in minutes.
    - Authentication
    - Maintaining a heartbeat
    - Sequence number management and resend requests
- Fast, easy to understand message processing pipeline based on a modern ``async and await`` implementation. 
- Easily extendable architecture - modular 'apps' can be added to the pipeline stack to add new application logic.
   
    ```python
    PIPELINE_APPS = [
        "my_app.apps.SecretAlgoTradingRecipe",     # <-- Your application logic
        "wtfix.apps.admin.HeartbeatApp",           # Heartbeat monitoring and maintenance
        "wtfix.apps.admin.AuthenticationApp",      # Login / logout handling
        "wtfix.apps.admin.SeqNumManagerApp",       # Message gap detection and filling
        "wtfix.apps.parsers.RawMessageParserApp",  # Message parsing: Logon (A): {BeginString (8):FIX.4.4 | BodyLength (9):99 | MsgType (35):A | MsgSeqNum (34):1 | SenderCompID (49):SENDER | SendingTime (52):20190305-08:45:45.979 | TargetCompID (56):TARGET | EncryptMethod (98):0 | HeartBtInt (108):30 | Username (553):USERNAME | Password (554):PASSWORD | ResetSeqNumFlag (141):Y | CheckSum (10):94}
        "wtfix.apps.wire.WireCommsApp",            # Raw message encoding / decoding: b'8=FIX.4.4\x019=99\x0135=A\x0134=1\x0149=SENDER\x0152=20190305-08:42:32.793\x0156=TARGET\x0198=0\x01108=30\x01553=USERNAME\x01554=PASSWORD\x01141=Y\x0110=081\x01'
        "wtfix.apps.sessions.ClientSessionApp",    # HTTP session management
    ]
    ```
    
- Convenient message hooks for adding new apps to the message processing pipeline:
    ```python
    from wtfix.apps.base import MessageTypeHandlerApp, on
    from wtfix.protocol.common import MsgType
    from wtfix.conf import logger
  
    class SecretAlgoTradingRecipe(MessageTypeHandlerApp):

        @on(MsgType.Logon)  # Only invokved when 'Logon (type A)' messages are received.
        def on_logon(self, message):
            self.send_security_definition_request()
            return message
          
        def on_receive(self, message):  # Invoked for every type of message
          logger.info(f"Received message {message}!")
    ```

- A Message tag syntax with convenience methods that are kind to humans. Example ``Logon`` message:

    ```python
    >>> from wtfix.message import admin
    >>> from wtfix.protocol.common import Tag
    
    >>> logon_msg = admin.LogonMessage("my_username", "my_password", heartbeat_int=b"30")
    
    # Determining the message type
    >>> logon_msg.type
    'A'
  
    >>> logon_msg.name
    'Logon'
  
    >>> logon_msg.seq_num
    1

    # Various ways for accessing message tags
    >>> logon_msg[108]  # Using old school tag number
    (108, b"30")
  
    >>> logon_msg[Tag.HeartBtInt]  # Using Tag name as per FIX specification
    (108, b"30")
  
    >>> logon_msg.HeartBtInt  # Using shortcut approach
    (108, b"30")
    ```    
- A [unicode sandwich](https://nedbatchelder.com/text/unipain.html) based approach means that you do not need to deal with bytestrings...
 
    ```python
    # Duck typing for doing tag value comparisons
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
- ...with on the fly type conversions:
    ```python
    >>> logon_msg.HeartBtInt.as_str
    '30'
    >>> logon_msg.HeartBtInt.as_int
    30
    ```
- A very forgiving approach to repeating groups of message tags:
    ```python
    from wtfix.message.message import generic_message_factory
  
    # If you provide a group template, then messages are stored in a more efficient 'OrderedDict'
    >>> msg = generic_message_factory((1, "a"), (2, 2), (3, "1st_group_tag3"), (4, "1st_group_tag_4"), (3, "2nd_group_tag3"), (4, "2nd_group_tag_4"), group_templates={2: [3, 4,]})
    >>> msg_.fields
    OrderedDict([(1, (1, a)), (2, [(2, 2)]:[(3, 1st_group_tag3), (4, 1st_group_tag_4)], [(3, 2nd_group_tag3), (4, 2nd_group_tag_4)])])
    
    # ...providing fast group and group instance lookups:
    >>> group = msg.get_group(2)
    # Determine the number of instances in the group
    >>> group.size
    2
  
    # Retrive the second group instance
    >>> group.instances[1]
    [(3, 2nd_group_tag3), (4, 2nd_group_tag_4)]
   
    # Without a pre-defined group template we fall back to using a (slightly slower) list structure for representing message fields internally
    >>> msg = generic_message_factory((1, "a"), (2, 2), (3, "1st_group_tag3"), (4, "1st_group_tag_4"), (3, "2nd_group_tag3"), (4, "2nd_group_tag_4"))
    >>> msg_.fields
    [(1, a), (2, 2), (3, 1st_group_tag3), (4, 1st_group_tag_4), (3, 2nd_group_tag3), (4, 2nd_group_tag_4)]
  
    ```
    
## Project Resources

- [Changelog](docs/changelog.md)
- [Release procedures](docs/releasing.md)

## Inspired By

- [slowbreak](https://pypi.org/project/slowbreak/)'s message processing pipeline and ``@on`` decorator
- [simplefix](https://github.com/da4089/simplefix)'s approach to raw message processing
