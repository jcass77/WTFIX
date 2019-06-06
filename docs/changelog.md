# Changelog

This changelog is used to track all major changes to WTFIX.

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
