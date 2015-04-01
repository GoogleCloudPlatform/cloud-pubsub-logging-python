# -*- coding: utf-8 -*-
# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Python logging handler implementation for Cloud Pub/Sub.

This module has logging.handlers.BufferingHandler implementation which
sends the logs to Cloud Pub/Sub[1]. The logs are kept in an internal
buffer by default. If the buffer becomes full (capacity), or the given
log record has a level higher than flush_level, the handler will
transmit the buffered logs to Cloud Pub/Sub.

By default, this log handler will try to keep the logs as much as
possible, even upon intermittent failure on Cloud Pub/Sub API. If
you're concerned about indifinitely growing buffer size in such cases,
you should set buf_hard_limit, then the buffer will be cut of at the
specified size. In that case, you may want to consider having another
backup logging handler backed by the local disk or something.

[1]: https://cloud.google.com/pubsub/docs

"""


import base64
import logging
import logging.config
import logging.handlers
import os
import sys

import httplib2
from apiclient import discovery
from apiclient import errors
from oauth2client.client import GoogleCredentials

__version__ = '0.1.6'


DEFAULT_BATCH_NUM = 1000
DEFAULT_RETRY_COUNT = 5
MAX_BATCH_SIZE = 1000
PUBSUB_SCOPES = ["https://www.googleapis.com/auth/pubsub"]


def compat_urlsafe_b64encode(v):
    """A urlsafe ba64encode which is compatible with Python 2 and 3."""
    if sys.version_info[0] == 3:
        return base64.urlsafe_b64encode(v.encode('UTF-8')).decode('ascii')
    else:
        return base64.urlsafe_b64encode(v)


class RecoverableError(Exception):
    """A special error case we'll ignore."""
    pass


class PubsubHandler(logging.handlers.BufferingHandler):
    """A logging handler to publish log messages to Cloud Pub/Sub."""
    def __init__(self, topic, capacity=DEFAULT_BATCH_NUM,
                 retry=DEFAULT_RETRY_COUNT, flush_level=logging.CRITICAL,
                 buf_hard_limit=-1, client=None):
        """The constructor of the handler.

        Args:
          topic: Cloud Pub/Sub topic name to send the logs.
          capacity: The maximum buffer size, defaults to 1000.
          retry: How many times to retry upon Cloud Pub/Sub API failure,
                 defaults to 5.
          flush_level: Minimum log level that, when seen, will flush the logs,
                       defaults to logging.CRITICAL.
          buf_hard_limit: Maximum buffer size to hold the logs, defaults to -1
                          which means unlimited size.
          client: An optional Cloud Pub/Sub client to use. If not set, one is
                  built automatically, defaults to None.
        """
        super(PubsubHandler, self).__init__(capacity)
        self._topic = topic
        self._retry = retry
        self._flush_level = flush_level
        self._buf_hard_limit = buf_hard_limit
        if client:
            self._client = client
        else:
            credentials = GoogleCredentials.get_application_default()
            if credentials.create_scoped_required():
                credentials = credentials.create_scoped(PUBSUB_SCOPES)
            http = httplib2.Http()
            credentials.authorize(http=http)
            self._client = discovery.build('pubsub', 'v1beta2', http=http)

    def _publish(self, body):
        """Publishes the specified body to Cloud Pub/Sub.

        Args:
          body: A request body for Cloud Pub/Sub publish call.

        Raises:
          errors.HttpError When the Cloud Pub/Sub API call fails with
                           unrecoverable reasons.
          RecoverableError When the Cloud Pub/Sub API call fails with
                           intermittent errors.
        """
        try:
            self._client.projects().topics().publish(
                topic=self._topic, body=body).execute(
                    num_retries=self._retry)
        except errors.HttpError as e:
            if e.resp.status >= 400 and e.resp.status < 500:
                # Publishing failed for some non-recoverable reason. For
                # example, perhaps the service account doesn't have a
                # permission to publish to the specified topic, or the topic
                # simply doesn't exist.
                raise
            else:
                # Treat this as a recoverable error.
                raise RecoverableError()

    def flush(self):
        """Transmits the buffered logs to Cloud Pub/Sub."""
        self.acquire()
        try:
            while self.buffer:
                body = {'messages':
                        [{'data': compat_urlsafe_b64encode(self.format(r))}
                            for r in self.buffer[:MAX_BATCH_SIZE]]}
                self._publish(body)
                self.buffer = self.buffer[MAX_BATCH_SIZE:]
        except RecoverableError:
            # Cloud Pub/Sub API didn't receive the logs, most
            # likely because of intermittent errors. This handler
            # ignores this case and keep the logs in its buffer in
            # a hope of future success.
            pass
        finally:
            # Cut off the buffer at the _buf_hard_limit.
            # The default value of -1 means unlimited buffer.
            if self._buf_hard_limit != -1:
                self.buffer = self.buffer[:self._buf_hard_limit]
            self.release()

    def shouldFlush(self, record):
        """Should the handler flush its buffer?

        Returns true if the buffer is up to capacity, or the given
        record has a level greater or equal to flush_level.
        """
        return (record.levelno >= self._flush_level
                or (len(self.buffer) >= self.capacity))


if __name__ == '__main__':
    logger = None
    if len(sys.argv) == 2:
        topic = sys.argv[1]
        pubsub_handler = PubsubHandler(topic=topic)
        pubsub_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

        logger = logging.getLogger('root')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(pubsub_handler)
    else:
        logging.config.fileConfig(os.path.join('examples', 'logging.conf'))
        logger = logging.getLogger('root')
    for i in range(99):
        logger.info('log message %03d.', i)
    logger.critical('Flushing')
