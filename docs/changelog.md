# Changelog

This changelog is used to track all major changes to WTFIX.

## v0.4.0 (2019-03-12)

**Enhancements**

- Split logging app into separate inbound and outbound processors so that the respective loggers can be injected in
different parts of the pipeline.
- Add JSON encoder / decoder for FieldSets - allows messages to be JSON encoded.

**Fixes**

- Fix WSGI callable to use ``session_name`` parameter correctly.

**Breaking changes**

- FIX messages that are submitted to the pipeline via ``RESTfulServiceApp`` no longer need to be pickled. Use
to convert any messages to be sent to JSON instead ``encoders.to_json(message)``. This should be more portable with
better cross-platform support.

## v0.3.0 (2019-03-10)

**Enhancements**

- Move `wsgi.py` to global `config` package.
- Add gunicorn support for running WTFIX and Flask in production environments.
- Add guidelines for doing production deployments.
- Provide ``JsonResultResponse`` structure for wrapping REST API responses.

**Fixes**

- Fix WSGI callable to use ``session_name`` parameter correctly.

**Breaking changes**

- Move ``wtfix.apps.api.RESTfulServiceApp`` to its own package at ``wtfix.apps.api.rest.RESTfulServiceApp``.


## v0.2.0 (2019-03-10)

**Enhancements**

- Add support for configuring multiple FIX sessions using the ``SESSIONS`` config parameter.
- Different pipeline connections can now be initiated by using the ``--sessions`` command line parameter with ``run_client.py``.
- New ``LoggingApp`` for logging of inbound and outbound messages.
- New ``RESTfulServiceApp`` for sending messages via a REST API.

**Fixes**
- Don't raise an exception if a heartbeat message (0) is received unexpectedly.

**Breaking changes**

- Rename ``SENDER_COMP_ID`` parameter to ``SENDER`` and ``TARGET_COMP_ID`` to ``TARGET``.

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
