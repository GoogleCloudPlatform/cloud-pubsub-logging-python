cloud-pubsub-logging-python
===========================

    Logging handlers for publishing the logs to Cloud Pub/Sub.

|pypi| |build| |coverage|

You can use the `pubsub_logging.PubsubHandler` or `pubsub_logging.AsyncPubsubHandler` to publish the logs to `Cloud Pub/Sub`_. You can use this module with `the standard Python logging module`_. It's recommended that you use `AsyncPubsubHandler`. `PubsubHandler` exists only for backward compatibility.

.. _Cloud Pub/Sub: https://cloud.google.com/pubsub/docs/
.. _the standard Python logging module: https://docs.python.org/2/library/logging.html

Supported version
-----------------

Python 2.7 and Python 3.4 are supported.

Installation
------------

::

    $ pip install pubsub-logging

How to use
----------

Here is an example configuration file.

::

    [loggers]
    keys=root

    [handlers]
    keys=asyncPubsubHandler

    [formatters]
    keys=simpleFormatter

    [logger_root]
    level=NOTSET
    handlers=asyncPubsubHandler

    [handler_asyncPubsubHandler]
    class=pubsub_logging.AsyncPubsubHandler
    level=DEBUG
    formatter=simpleFormatter
    # Replace {project-name} and {topic-name} with actual ones.
    # The second argument indicates number of workers.
    args=('projects/{project-name}/topics/{topic-name}', 10)

    [formatter_simpleFormatter]
    format=%(asctime)s - %(name)s - %(levelname)s - %(message)s

How to use this config file.

.. code:: python

    logging.config.fileConfig(os.path.join('examples', 'async.conf'))
    logger = logging.getLogger('root')
    logger.info('My first message.')

Here is a dynamic usage example.

.. code:: python

    pubsub_handler = AsyncPubsubHandler(topic=topic)
    pubsub_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    logger = logging.getLogger('root')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(pubsub_handler)
    logger.info('My first message.')

The logs are kept in a buffer first, then moved to the process safe queue, and then the background child processes automatically pick up and send them to Cloud Pub/Sub. The flush call blocks until all of the logs are sent to Cloud Pub/Sub.

Authentication
--------------

The module uses the `Application Default Credentials`_. You can configure the authentication as follows.

.. _Application Default Credentials: https://developers.google.com/accounts/docs/application-default-credentials

Authentication on App Engine
----------------------------

It should work out of the box. If you're getting an authorization error, please make sure that your App Engine service account has an `Editor` or greater permission on your Cloud project.

Authentication on Google Compute Engine
---------------------------------------

When creating a new instance, please add the Cloud Pub/Sub scope `https://www.googleapis.com/auth/pubsub` to the service account of the instance.

Authentication anywhere else
----------------------------

As `the documentation suggests`_, create a new service account and download its JSON key file, then set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` pointing to the JSON key file. Please note that this service account must have `Editor` or greater permissions on your Cloud project.

.. _the documentation suggests: https://developers.google.com/accounts/docs/application-default-credentials#whentouse


.. |build| image:: https://travis-ci.org/GoogleCloudPlatform/cloud-pubsub-logging-python.svg?branch=master
   :target: https://travis-ci.org/GoogleCloudPlatform/cloud-pubsub-logging-python
.. |pypi| image:: https://img.shields.io/pypi/v/pubsub-logging.svg
   :target: https://pypi.python.org/pypi/pubsub-logging
.. |coverage| image:: https://coveralls.io/repos/GoogleCloudPlatform/cloud-pubsub-logging-python/badge.png?branch=master
   :target: https://coveralls.io/r/GoogleCloudPlatform/cloud-pubsub-logging-python?branch=master
