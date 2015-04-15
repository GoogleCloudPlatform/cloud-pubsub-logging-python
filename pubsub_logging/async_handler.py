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

This module provides a logging.Handler implementation which sends the
logs to Cloud Pub/Sub[1] asynchronously. The logs are kept in an
internal queue and child workers will pick them up and send them in
background.

[1]: https://cloud.google.com/pubsub/docs

"""

import logging
import multiprocessing as mp

try:
    from queue import Empty
except ImportError:  # pragma: NO COVER
    from Queue import Empty

from pubsub_logging import errors

from pubsub_logging.utils import compat_urlsafe_b64encode
from pubsub_logging.utils import get_pubsub_client
from pubsub_logging.utils import publish_body


BATCH_SIZE = 1000
DEFAULT_WORKER_SIZE = 1
DEFAULT_RETRY_COUNT = 10
DEFAULT_TIMEOUT = 1


class AsyncPubsubHandler(logging.Handler):
    """A logging handler to publish logs to Cloud Pub/Sub in background."""
    def __init__(self, topic, worker_size=DEFAULT_WORKER_SIZE, debug=False,
                 retry=DEFAULT_RETRY_COUNT, timeout=DEFAULT_TIMEOUT,
                 client=None, publish_body=publish_body, stderr_logger=None):
        """The constructor of the handler.

        Args:
          topic: Cloud Pub/Sub topic name to send the logs.
          worker_size: The initial worker size.
          debug: A flag for debug output.
          retry: How many times to retry upon Cloud Pub/Sub API failure,
                 defaults to 5.
          timeout: Timeout for BatchQueue.get.
          client: An optional Cloud Pub/Sub client to use. If not set, one is
                  built automatically, defaults to None.
          publish_body: A callable for publishing the Pub/Sub message,
                        just for testing purposes.
          stderr_logger: A logger for informing failures with this logger.
        """
        super(AsyncPubsubHandler, self).__init__()
        self._topic = topic
        self._debug = debug
        self._retry = retry
        self._client = client
        self._q = mp.JoinableQueue()
        self._should_exit = mp.Value('i', 0)
        self._children = []
        self._timeout = timeout
        self._threshold = BATCH_SIZE
        self._buf = []
        self._publish_body = publish_body
        if stderr_logger:
            self._stderr_logger = stderr_logger
        else:
            self._stderr_logger = logging.Logger('last_resort')
            self._stderr_logger.addHandler(logging.StreamHandler())
        for i in range(worker_size):
            p = mp.Process(target=self.send_loop, args=(self._q,))
            p.daemon = True
            self._children.append(p)
            p.start()

    def send_loop(self, q):  # pragma: NO COVER
        """Process loop for indefinitely sending logs to Cloud Pub/Sub."""
        if self._client:
            client = self._client
        else:  # pragma: NO COVER
            client = get_pubsub_client()
        while not self._should_exit.value:
            logs = []
            try:
                logs = q.get(block=True, timeout=self._timeout)
            except Empty:
                pass
            if not logs:
                continue
            try:
                body = {'messages':
                        [{'data': compat_urlsafe_b64encode(self.format(r))}
                            for r in logs]}
                self._publish_body(client, body, self._topic, self._retry,
                                   debug=self._debug)
            except errors.RecoverableError as e:
                # Records the exception and puts the logs back to the deque
                # and prints the exception to stderr.
                q.put(logs)
                self._stderr_logger.exception(e)
            except Exception as e:
                self._stderr_logger.exception(e)
                self._stderr_logger.warn('There was a non recoverable error, '
                                         'exiting.')
                exit()
            q.task_done()

    def emit(self, record):
        """Puts the record to the internal queue."""
        self._buf.append(record)
        if len(self._buf) == self._threshold:
            self._q.put(self._buf)
            self._buf = []

    def flush(self):
        """Blocks until the queue becomes empty."""
        with self.lock:
            if self._buf:
                self._q.put(self._buf)
                self._buf = []
            self._q.join()

    def close(self):
        """Joins the child processes and call the superclass's close."""
        with self.lock:
            self.flush()
            self._should_exit.value = 1
            for p in self._children:
                p.join()
        super(AsyncPubsubHandler, self).close()
