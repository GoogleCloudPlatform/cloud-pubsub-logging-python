# A logging handler for publishing the logs to Cloud Pub/Sub.

You can use the pubsub_logging.PubsubHandler to publish the logs to [Cloud Pub/Sub](https://cloud.google.com/pubsub/docs/). You can use this module with [the standard Python logging module](https://docs.python.org/2/library/logging.html).

## Supported version
Python 2.7 and 3.4 are supported.

## How to use
An example configuration can be found in `examples/logging.conf`. A dynamic usage example is included in `pubsub_logging.py`.

## Authentication
The module uses the [Application Default Credentials](https://developers.google.com/accounts/docs/application-default-credentials). You can configure the authentication as follows.

### Authentication on App Engine

It should work out of the box. If you're getting an authorization error, please make sure that your App Engine service account has an `Editor` or greater permission on your Cloud project.

### Authentication on Google Compute Engine

When creating a new instance, please add the Cloud Pub/Sub scope `https://www.googleapis.com/auth/pubsub` to the service account of the instance.

### Authentication anywhere else

As [the documentation suggests](https://developers.google.com/accounts/docs/application-default-credentials#whentouse), create a new service account and download its JSON key file, then set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` pointing to the JSON key file. Please note that this service account must have `Editor` or greater permissions on your Cloud project.
