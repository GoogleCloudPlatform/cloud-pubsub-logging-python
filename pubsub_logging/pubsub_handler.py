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
you should set buf_hard_limit, then the buffer will be cut off at the
specified size. In that case, you may want to consider having another
backup logging handler backed by the local disk or something.

[1]: https://cloud.google.com/pubsub/docs

"""

import logging

from pubsub_logging.errors import RecoverableError
from pubsub_logging.utils import compat_urlsafe_b64encode
from pubsub_logging.utils import get_pubsub_client
from pubsub_logging.utils import publish_body


DEFAULT_BATCH_NUM = 1000
DEFAULT_RETRY_COUNT = 5
MAX_BATCH_SIZE = 1000


class PubsubHandler(logging.handlers.BufferingHandler):
    """A logging handler to publish log messages to Cloud Pub/Sub."""
    def __init__(self, topic, capacity=DEFAULT_BATCH_NUM,
                 retry=DEFAULT_RETRY_COUNT, flush_level=logging.CRITICAL,
                 buf_hard_limit=-1, client=None, publish_body=publish_body):
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
          publish_body: A callable for publishing the Pub/Sub message,
                        just for testing and benchmarking purposes.
        """
        super(PubsubHandler, self).__init__(capacity)
        self._topic = topic
        self._retry = retry
        self._flush_level = flush_level
        self._buf_hard_limit = buf_hard_limit
        self._publish_body = publish_body
        if client:
            self._client = client
        else:  # pragma: NO COVER
            self._client = get_pubsub_client()

    def flush(self):
        """Transmits the buffered logs to Cloud Pub/Sub."""
        self.acquire()
        try:
            while self.buffer:
                body = {'messages':
                        [{'data': compat_urlsafe_b64encode(self.format(r))}
                            for r in self.buffer[:MAX_BATCH_SIZE]]}
                self._publish_body(self._client, body, self._topic,
                                   self._retry)
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
