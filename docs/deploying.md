## Deploying

Deploying WTFIX to staging or production environments generally involves the following steps:

- Set the ``WTFIX_SETTINGS_MODULE`` environment variable to ``config.settings.staging`` or ``config.settings.production``
as the case may be.

- Ensure that the ``DEBUG`` configuration parameter is set to ``False``.

- If the pipeline has been configured to include the ``RESTfulServiceApp``, then you will also need to configure a
WSGI HTTP server for hosting the APIs (Flask's built-in server is [not suitable for production](http://flask.pocoo.org/docs/deploying/)).
WTFIX comes with support for [gunicorn](https://gunicorn.org) out of the box, though any well-supported WSGI container
should do.

```bash
    gunicorn --workers 1 --bind unix:<path_to_your_project>/wtfix.sock 'config.wsgi:get_wsgi_application(session_name="default")'
```

> **NOTE**: many FIX servers do not allow multiple connections using the same logon credentials, so it probably noes not
make sense to run more than one worker process. You should also consider monitoring the above process with something
like [supervisord](http://supervisord.org):

```bash
[program:wtfix]
command=<path_to_your_gunicorn_binary>/gunicorn --workers 1 --bind unix:<path to your project>/wtfix.sock 'config.wsgi:get_wsgi_application(session_name="default")'
directory=<path_to_your_project_dir>
autostart=true
autorestart=true
stderr_logfile=/var/log/wtfix.err.log
stdout_logfile=/var/log/wtfix.out.log
```
