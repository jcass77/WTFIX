# Changelog

This changelog is used to track all major changes to WTFIX.


## v0.16.0 (2020-09-11)

**Enhancements**

- FIX protocol specification: look up class attributes in parent classes as well. This allows new FIX protocol
  specifications, which can include custom tags and message types, to be derived from a standard base protocol
  definition.
- Stop processing messages as soon as an unhandled exception occurs. This ensures that all apps have the same state
  up until the point at which the exception was raised.
- The pipeline will now not process any messages for apps that have already been shut down.
- `BasePipeline.stop()` now accepts an optional keyword argument that can be used to pass the exception that caused
  the pipeline to be stopped. This makes it possible to distinguish between normal and abnormal pipeline shutdowns so
  that OS exit codes can be set properly by the calling process.

**Fixes**

- Remove tag numbers >= 956 from the standard FIX 4.4 protocol definition. These all fall within the customer-defined
  number range and do not form part of the official standard.
- Remove non-standard message types from the FIX 4.4. protocol definition.
- Don't re-raise exceptions in asyncio tasks that trigger a pipeline shutdown. This prevents the application's `stop()`
  method from being interrupted before it has been fully processed.


## v0.15.3 (2020-08-11)

**Fixes**

- Avoid `AttributeError` when a `ConnectionError` occurs in the `client_session` app.
- Refactor task cancellation: client should take responsibility for final task cancellation / cleanup instead of the
  pipeline. This ensures that the client itself is not also cancelled as part of a pipeline shutdown.
- Only call `super().stop()` after an app has completed all of its own shutdown routines.
- Don't allow misbehaving apps from interrupting a pipeline shutdown. This ensures that the pipeline can always be
  shut down, and all outstanding asyncio tasks cancelled, even if one or more apps raise and exceptions while stopping.


## v0.15.2 (2020-08-05)

**Fixes**

- `client_session`: Don't wait for `writer` to close when shutting down in order to avoid hangs due to network errors.
- Use the recommended `asyncio.create_task` to create new Tasks, which is preferred to `asyncio.ensure_future`.
- Fix issue that caused the `client_session` listener task to hang during shutdown.


## v0.15.1 (2020-07-28)

**Fixes**

- Fix cancellation of various `asyncio` tasks causing the pipeline to hang during shutdown.


## v0.15.0 (2020-07-28)

**Enhancements**

- Refactor graceful shutdown of pipeline to cancel all tasks in parallel and log all exceptions.
- Update exception handling routines to reference the standard asyncio exceptions that were moved to the new
  `asyncio.exceptions` package in Python 3.8.
- Now requires Python >= 3.8.
- **BREAKING CONFIG CHANGES** (please update your `.env` and settings files in `wtfix.config.settings`):
    - Rename `REDIS_URI` config parameter to `REDIS_WTFIX_URI` so that WTFIX can be incorporated into existing
      applications without affecting their configuration settings.

**Fixes**

- `SeqNumManagerApp`: wait until a buffered Message has been completely processed before submitting the next one.
- `RedisPubSubApp`: Release Redis connection before attempting to close the Redis pool.

## v0.14.3 (2020-04-29)

**Enhancements**

- Relax dependency version requirements in setup.py.
- Update dependencies to latest major versions.

## v0.14.2 (2019-12-16)

**Fixes**

- Re-raise all exceptions that cause the pipeline to terminate abnormally so that they can be reported and dealt
  with at the operating system level. Useful if pipeline is being monitored by something like [supervisord](http://supervisord.org).


## v0.14.1 (2019-11-27)

**Fixes**

- Set logging level of 'wtfix' logger to `LOGGING_LEVEL` when it is first requested.
- Fix bug in `_replay_buffered_messages` that prevented buffered messages from being received.


## v0.14.0 (2019-11-15)

**Enhancements**

- Fix Python 3.8 compatibility issues.
- Switch to using a context manager for managing the active FIX connection / protocol.


## v0.13.0 (2019-11-14)

**Enhancements**

- **BREAKING CONFIG CHANGES** (please update your settings files in `wtfix.config.settings`):
    - The MESSAGE_STORE parameters now form part of the CONNECTION section. This allows individual message stores to
      be configured when multiple connections need to be run simultaneously.
    - Add configuration option for specifying which JSON encoder / decoder to use when adding messages to a message
      store.
    - The FIX protocol and version can now be configured for individual CONNECTIONS. This lays the foundation for
      supporting various different protocols and versions in the future. FIX 4.4 is currently the default.

- Add `PipelineTerminationApp` and use `del` to encourage the Python interpreter to garbage collect a message once it
  has reached either end of the pipeline.
- Upgrade aioredis dependency to version 1.3
- Remove dependency on [unsync](https://github.com/alex-sherman/unsync) which has become largely redundant with the new async features released as part
  of Python 3.7.
- Now requires Python >= 3.7.


## v0.12.4 (2019-09-02)

**Fixes**

- Update dependencies to latest versions.
- Change `RedisPubSubApp` to allow subclasses to override the Redis sending channel name via
  `RedisPubSubApp.SEND_CHANNEL`

## v0.12.3 (2019-07-04)

**Fixes**

- Fixed encoding of `PossDupFlag` in `EncoderApp`.
- Fixed setting of `OrigSendingTime` tag for messages that are resent.


## v0.12.2 (2019-07-04)

**Fixes**

- `ClientSessionApp`: handle `NoneType` error when shutting down.

## v0.12.1 (2019-07-04)

**Fixes**

- Prevent a pipeline shutdown from being triggered multiple times.
- Less verbose logging of connection errors that occur during shutdown / logout.


## v0.12.0 (2019-06-06)

**Enhancements**

- Repeating group templates can now be configured on a per-message-type basis.


## v0.11.0 (2019-05-27)

**Enhancements**

- Make username and password optional for Logon messages.
- Fixed an issue that caused only one Heartbeat timer to be used for both sending and receiving messages.
- Collections of FIXMessages can now be sorted by their sequence numbers.

**Fixes**

- Set `SendingTime` before message is added to the message store (Fixes [#2](https://github.com/jcass77/WTFIX/issues/2)).
- Enforce serial processing: wait until a message has been propagated through the entire pipeline before receiving the next message.


## v0.10.0 (2019-05-13)

**Enhancements**

- Automatically start a new session if no relevant .sid file can be found.
- Heartbeat monitor now proactively sends heartbeats as well, in compliance with the FIX protocol specification.
- Pipeline now shuts down gracefully on SIGTERM and SIGINT signals in addition to CTRL+C.

**Fixes**

- Fix path to .sid files.


## v0.9.0 (2019-05-02)

**Enhancements**

- Added RedisPubSubApp for sending / receiving messages using the redis Pub/Sub messaging paradigm.
- Various performance optimizations.

**Fixes**

- Add missing dependencies to setup.py.

## v0.8.0 (2019-04-30)

**Enhancements**

- FIX sessions are now resumed between different connections by default. Pass parameter `-new_session` when calling
the pipeline in order to reset sequence numbers and initialize a new session.
- Rename 'sessions' to 'connections' to align with FIX protocol terminology.
- Gap fill processing is now more reliable, and will queue messages that are received out of order until the gaps have
been filled.
- Set exit codes on pipeline termination so that caller can take appropriate action.
- Add `MessageStoreApp`, with default implementations for in-memory and redis-based stores for caching and / or
persisting messages to database.
- Convert all `on_send` and `on_receive` handlers to async and await.
- Messages are now sent in separate Tasks to avoid holding up the main event loop.
- AuthenticationApp now blocks all incoming and outgoing messages until authentication has been completed.

## v0.7.0 (2019-04-21)

**Enhancements**

- Add support for deleting a Field from a FieldMap by its tag name. E.g. `del message.PossDupFlag`.
- Add pre-commit hooks for checking code style and quality.
- Fix PEP8 code style violations reported by flake8.
- Update code quality dependencies (flake, black, etc.).

## v0.6.0 (2019-04-01)

**Enhancements**

- Refactor `FieldSet` to better emulate the Python built-it container types.
- Rename `FieldSet` to `FieldMap`, `ListFieldSet` to `FieldList`, and `OrderedDictFieldSet` to `FieldDict`. Deprecate
and remove old classes.
- Implement all of the [`MutableSequence`](https://docs.python.org/3/library/collections.abc.html#module-collections.abc)
abstract base class methods for `Field`.
- Operations can now be performed directly between `Field.value` and Python's built-in literals (e.g.
`Field(1, "abc") + "def"` will return `Field(1, "abcdef")`).
- Replace `as_str`, `as_bool`, and `as_int` with Python special methods to allow more natural casting using `str()`,
`bool()`, and `int()`. Add new `float()` method for casting `Field`s to float.
- Deprecate and remove `FieldValue` class.
- Field ordering is no longer significant when comparing `FieldMap`s with other `Sequence`s.
- Replace `raw` property for converting `Field`s and `FieldMap`s to a byte sequence with `bytes()`.
- Add `frombytes()` and `fields_frombytes()` methods to `Field` for creating new `Field` instances from byte sequences.
- Optimize memory usage of `Field`s by adding a `__slots__` attribute.
- Make `Field` instances hashable by implementing `__hash__` and `__eq__`.
- Add `__format__` implementation to `Field`, with a custom `t` option, for printing fields with their tag names.
- Convert the FIX representation of 'null' (`"-2147483648"`) to `None` when constructing a `Field` for more natural
usage in Python.
- Now Encodes boolean Field values to "Y/N".
- Remove `Message.get_group()` and `Message.set_group()` in favor of handling group fields like any other Field in the
message.
- Remove deprecated `InvalidGroup` exception.

## v0.5.0 (2019-03-15)

**Enhancements**

- JSON encode / decode directly to and form FIXMessage instead of FieldSet.

## v0.4.0 (2019-03-12)

**Enhancements**

- Split logging app into separate inbound and outbound processors so that the respective loggers can be injected in
different parts of the pipeline.
- Add JSON encoder / decoder for FieldSets - allows messages to be JSON encoded.

**Fixes**

- Fix WSGI callable to use ``session_name`` parameter correctly.

## v0.3.0 (2019-03-10)

**Enhancements**

- Move `wsgi.py` to global `config` package.
- Add gunicorn support for running WTFIX and Flask in production environments.
- Add guidelines for doing production deployments.
- Provide ``JsonResultResponse`` structure for wrapping REST API responses.

**Fixes**

- Fix WSGI callable to use ``session_name`` parameter correctly.

## v0.2.0 (2019-03-10)

**Enhancements**

- Add support for configuring multiple FIX sessions using the ``SESSIONS`` config parameter.
- Different pipeline connections can now be initiated by using the ``--sessions`` command line parameter with ``run_client.py``.
- New ``LoggingApp`` for logging of inbound and outbound messages.
- New ``RESTfulServiceApp`` for sending messages via a REST API.

**Fixes**
- Don't raise an exception if a heartbeat message (0) is received unexpectedly.

## v0.1.2 (2019-03-05)

- Fix test build dependencies.

## v0.1.1 (2019-03-05)

- Add missing aiofiles dependency.
- Link repository to coveralls.io and Travis-CI
- Update README with various GitHub badges.

## v0.1.0 (2019-03-05)

- First public alpha release.
- Now implements all standard admin messages.
- Update README

## v0.0.3 (2019-02-08)

- Pre-alpha internal testing release.

## v0.0.2 (2018-12-11)

- Pre-alpha internal testing release.

## v0.0.1 (2018-12-11)

- Pre-alpha internal testing release.
