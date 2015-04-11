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

"""A special queue class for the Python logging handlers."""

try:
    from queue import Empty
except ImportError:
    from Queue import Empty

try:
    import threading
except ImportError:  # pragma: NO COVER
    import dummy_threading as threading

try:
    from time import monotonic as time
except ImportError:
    from time import time

from collections import deque


class BatchQueue(object):
    """A special queue object that you can get a batch of items."""

    def __init__(self, batch_size=1000):
        self._batch_size = batch_size
        self._q = deque()
        self._mutex = threading.Lock()

        # Notify has_plenty whenever an item is added and the size of
        # the queue becomes more than the batch_size.
        self.has_plenty = threading.Condition(self._mutex)

        # Notify done whenever the number of unfinished tasks drops to zero.
        self.done = threading.Condition(self._mutex)
        self.unfinished_tasks = 0

    def _qsize(self):
        """Returns the size of the queue."""
        return len(self._q)

    def _put_multi(self, items):
        """Puts new items in the queue."""
        self._q.extend(items)

    def _put(self, item):
        """Puts a new item in the queue."""
        self._q.append(item)

    def _get(self):
        """Returns an item from the queue."""
        return self._q.popleft()

    def task_done(self, num=1):
        """Indicate that a formerly enqueued task is complete.

        Used by Queue consumer threads.  For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.

        If a join() is currently blocking, it will resume when all items
        have been processed (meaning that a task_done() call was received
        for every item that had been put() into the queue).

        Raises a ValueError if called more times than there were items
        placed in the queue.

        Args:
          num: Number of tasks to mark as done. Defaults to 1.
        """
        with self.done:
            unfinished = self.unfinished_tasks - num
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError('task_done() called too many times')
                self.done.notify_all()
            self.unfinished_tasks = unfinished

    def join(self):
        """Blocks until all items in the Queue have been gotten and processed.

        The count of unfinished tasks goes up whenever an item is added to the
        queue. The count goes down whenever a consumer thread calls task_done()
        to indicate the item was retrieved and all work on it is complete.

        When the count of unfinished tasks drops to zero, join() unblocks.
        """
        with self.done:
            while self.unfinished_tasks:
                self.done.wait()

    def put_multi(self, items):
        """Put items into the queue.

        Args:
          items: Items to put into the queue.
        """
        with self._mutex:
            self._put_multi(items)
            self.unfinished_tasks += len(items)
            if self._qsize() >= self._batch_size:
                self.has_plenty.notify()

    def put(self, item):
        """Put an item into the queue.

        Args:
          item: An item to put into the queue.
        """
        with self._mutex:
            self._put(item)
            self.unfinished_tasks += 1
            if self._qsize() >= self._batch_size:
                self.has_plenty.notify()

    def get(self, timeout=0):
        """Remove and return items from the queue.

        It blocks at most 'timeout' (default 0) seconds and raises the
        Empty exception if no item was available within that time or
        returns some items.
        """
        with self.has_plenty:
            if timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = time() + timeout
                while not self._qsize() >= self._batch_size:
                    remaining = endtime - time()
                    if remaining <= 0.0:
                        break
                    self.has_plenty.wait(remaining)
            items = []
            while self._qsize() and len(items) < self._batch_size:
                items.append(self._get())
            if not items:
                raise Empty
            return items
