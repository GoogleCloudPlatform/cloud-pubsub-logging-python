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

"""Unit tests for pubsub_logging."""


import logging
import threading
import unittest

from apiclient import errors

import mock

from mock import patch

import pubsub_logging

from pubsub_logging import queue
from pubsub_logging.errors import RecoverableError
from pubsub_logging.utils import compat_urlsafe_b64encode
from pubsub_logging.utils import publish_body


class CompatBase64Test(unittest.TestCase):
    """Test for compat_urlsafe_b64encode function."""

    def test_compat_urlsafe_b64encode(self):
        v = 'test'
        expected = 'dGVzdA=='
        result = compat_urlsafe_b64encode(v)
        self.assertEqual(expected, result)
        # Python3 route
        result = compat_urlsafe_b64encode(v, True)
        self.assertEqual(expected, result)


class BatchQueueTest(unittest.TestCase):
    """Test for queue.BatchQueue."""

    def setUp(self):
        self.q = queue.BatchQueue(batch_size=10)

    def test_negative_timeout_raises_ValueError(self):
        """Test if it raises ValueError with negative timeout."""
        def q_get():
            self.q.get(timeout=-1)
        self.assertRaises(ValueError, q_get)

    def test_too_much_task_done_raises_ValueError(self):
        """Test if it raises ValueError with too much task_done calls."""
        def q_task_done():
            self.q.task_done(num=1)
        self.assertRaises(ValueError, q_task_done)

    def test_put_and_get(self):
        """Test basic put and get operation."""
        values = [1, 2, 3]
        self.q.put(values)
        got = self.q.get(timeout=0.1)
        self.assertEqual(values, got)


class PublishBodyTest(unittest.TestCase):
    """Tests for utils.publish_body function."""
    RETRY = 3

    def setUp(self):
        self.mocked_client = mock.MagicMock()
        self.topic = 'projects/test-project/topics/test-topic'
        self.projects = self.mocked_client.projects.return_value
        self.topics = self.projects.topics.return_value
        self.topics_publish = self.topics.publish.return_value
        self.log_msg = 'Test message'
        self.expected_payload = compat_urlsafe_b64encode(
            self.log_msg)
        self.expected_body = {'messages': [{'data': self.expected_payload}]}
        self.r = logging.LogRecord('test', logging.INFO, None, 0, self.log_msg,
                                   [], None)

    def publish(self):
        publish_body(self.mocked_client, self.expected_body, self.topic,
                     self.RETRY)

    def test_publish_body(self):
        """Basic test for publish_body."""
        self.publish()
        self.topics.publish.assert_called_once_with(
            topic=self.topic, body=self.expected_body)
        self.topics_publish.execute.assert_called_with(num_retries=self.RETRY)

    def test_publish_body_raise_on_publish_404(self):
        """Tests if the flush method raises when publish gets a 404 error."""
        mocked_resp = mock.MagicMock()
        mocked_resp.status = 404
        mocked_resp.reason = 'Not Found'
        # 404 error
        self.topics_publish.execute.side_effect = [
            errors.HttpError(mocked_resp, 'Not found')
        ]
        self.assertRaises(errors.HttpError, self.publish)

    def test_flush_raise_on_publish_403(self):
        """Tests if the flush method raises when publish gets a 403 error."""
        mocked_resp = mock.MagicMock()
        mocked_resp.status = 403
        mocked_resp.reason = 'Access not allowed'
        # 403 error
        self.topics_publish.execute.side_effect = [
            errors.HttpError(mocked_resp, 'Access not allowed'),
        ]
        self.assertRaises(errors.HttpError, self.publish)

    def test_flush_ignore_recoverable(self):
        """Tests if we raise upon getting 503 error from Cloud Pub/Sub."""
        mocked_resp = mock.MagicMock()
        mocked_resp.status = 503
        mocked_resp.reason = 'Server Error'
        # 503 error
        self.topics_publish.execute.side_effect = [
            errors.HttpError(mocked_resp, 'Server Error'),
        ]
        self.assertRaises(RecoverableError, self.publish)
        self.topics.publish.assert_called_once_with(
            topic=self.topic, body=self.expected_body)
        self.topics_publish.execute.assert_called_once_with(
            num_retries=self.RETRY)


class CountPublishBody(object):
    """A simple counter that counts total number of messages."""
    def __init__(self):
        self.cnt = 0
        self.lock = threading.Lock()

    def __call__(self, client, body, topic, retry):
        self.lock.acquire()
        self.cnt += len(body['messages'])
        self.lock.release()


class AsyncPubsubHandlerTest(unittest.TestCase):
    """Tests for async_handler.AsyncPubsubHandler."""
    RETRY = 10

    def setUp(self):
        self.mocked_client = mock.MagicMock()
        self.topic = 'projects/test-project/topics/test-topic'
        self.handler = pubsub_logging.AsyncPubsubHandler(
            topic=self.topic, client=self.mocked_client, retry=self.RETRY,
            worker_size=10, timeout=0)

    def tearDown(self):
        self.handler.close()

    def test_single_message(self):
        """Tests if utils.publish_body is called with one message."""
        log_msg = 'Test message'
        r = logging.LogRecord('test', logging.CRITICAL, None, 0, log_msg, [],
                              None)
        expected_payload = compat_urlsafe_b64encode(log_msg)
        expected_body = {'messages': [{'data': expected_payload}]}
        counter = CountPublishBody()
        with patch('pubsub_logging.async_handler.publish_body',
                   side_effect=counter) as publish_body:
            self.handler.emit(r)
            self.handler.flush()
            self.assertEqual(1, counter.cnt)
            publish_body.assert_called_once_with(
                self.mocked_client, expected_body, self.topic, self.RETRY)

    def test_ignores_exceptions(self):
        """Tests if the handler ignores exceptions and drop the logs."""
        log_msg = 'Test message'
        r = logging.LogRecord('test', logging.CRITICAL, None, 0, log_msg, [],
                              None)
        expected_payload = compat_urlsafe_b64encode(log_msg)
        expected_body = {'messages': [{'data': expected_payload}]}
        counter = CountPublishBody()
        with patch('pubsub_logging.async_handler.publish_body',
                   side_effect=Exception()) as publish_body:
            self.handler.emit(r)
            self.handler.flush()
            publish_body.side_effect = counter
            self.handler.emit(r)
            self.handler.flush()
            self.assertEqual(1, counter.cnt)
            publish_body.assert_called_twice_with(
                self.mocked_client, expected_body, self.topic, self.RETRY)

    def test_total_message_count(self):
        """Tests if utils.publish_body is called with 10000 message."""
        log_msg = 'Test message'
        r = logging.LogRecord('test', logging.CRITICAL, None, 0, log_msg, [],
                              None)
        num = 10000
        counter = CountPublishBody()
        with patch('pubsub_logging.async_handler.publish_body',
                   side_effect=counter):
            for i in range(num):
                self.handler.emit(r)
            self.handler.flush()
            self.assertEqual(num, counter.cnt)


class PubsubHandlerTest(unittest.TestCase):
    """Tests for the emit method."""
    RETRY = 3
    BATCH_NUM = 2

    def setUp(self):
        self.mocked_client = mock.MagicMock()
        self.topic = 'projects/test-project/topics/test-topic'
        self.handler = pubsub_logging.PubsubHandler(
            topic=self.topic, client=self.mocked_client, retry=self.RETRY,
            capacity=self.BATCH_NUM)
        self.handler.flush = mock.MagicMock()

    def test_single_buff(self):
        """Tests if the log is stored in the internal buffer."""
        log_msg = 'Test message'
        r = logging.LogRecord('test', logging.INFO, None, 0, log_msg, [], None)

        self.handler.emit(r)
        self.assertEqual(1, len(self.handler.buffer))
        self.assertIs(r, self.handler.buffer[0])

    def test_critical_forces_flush(self):
        """Tests if a single CRITICAL level log forces flushing."""
        log_msg = 'Test message'
        r = logging.LogRecord('test', logging.CRITICAL, None, 0, log_msg, [],
                              None)

        self.handler.emit(r)
        self.handler.flush.assert_called_once()

    def test_custom_level_forces_flush(self):
        """Tests if a single INFO level log forces flushing."""
        self.handler._flush_level = logging.INFO
        log_msg = 'Test message'
        r = logging.LogRecord('test', logging.INFO, None, 0, log_msg, [], None)

        self.handler.emit(r)
        self.handler.flush.assert_called_once()

    def test_flush_when_full(self):
        """Tests if the flush is called when the buffer is full."""
        log_msg1 = 'Test message'
        log_msg2 = 'Test message2'
        r1 = logging.LogRecord('test', logging.INFO, None, 0, log_msg1, [],
                               None)
        r2 = logging.LogRecord('test', logging.INFO, None, 0, log_msg2, [],
                               None)

        self.handler.emit(r1)
        self.handler.flush.assert_not_called()

        self.handler.emit(r2)
        self.handler.flush.assert_called_once()


class PubsubHandlerFlushTest(unittest.TestCase):
    """Tests for the flush method of PubsubHandler."""
    RETRY = 3
    BATCH_NUM = 2

    def setUp(self):
        self.mocked_client = mock.MagicMock()
        self.topic = 'projects/test-project/topics/test-topic'
        self.handler = pubsub_logging.PubsubHandler(
            topic=self.topic, client=self.mocked_client, retry=self.RETRY,
            capacity=self.BATCH_NUM)
        self.log_msg = 'Test message'
        self.expected_payload = compat_urlsafe_b64encode(
            self.log_msg)
        self.expected_body = {'messages': [{'data': self.expected_payload}]}
        self.r = logging.LogRecord('test', logging.INFO, None, 0, self.log_msg,
                                   [], None)

    @patch('pubsub_logging.pubsub_handler.publish_body')
    def test_flush(self, publish_body):
        """Tests if the flush method calls publish_body."""
        self.handler.emit(self.r)

        self.handler.flush()
        publish_body.assert_called_once_with(
            self.mocked_client, self.expected_body, self.topic, self.RETRY)
        self.assertEqual(0, len(self.handler.buffer))

    @patch('pubsub_logging.pubsub_handler.publish_body')
    def test_flush_raise_on_publish_404(self, publish_body):
        """Tests if the flush raises upon 404 error from publish_body."""
        self.handler.emit(self.r)
        mocked_resp = mock.MagicMock()
        mocked_resp.status = 404
        mocked_resp.reason = 'Not Found'
        # 404 error
        publish_body.side_effect = errors.HttpError(mocked_resp, 'Not found')
        self.assertRaises(errors.HttpError, self.handler.flush)

    @patch('pubsub_logging.pubsub_handler.publish_body')
    def test_flush_ignore_recoverable(self, publish_body):
        """Tests if we ignore Recoverable error from publish_body."""
        self.handler.emit(self.r)
        publish_body.side_effect = RecoverableError()
        self.handler.flush()

        publish_body.assert_called_once_with(
            self.mocked_client, self.expected_body, self.topic, self.RETRY)
        self.assertEqual(1, len(self.handler.buffer))

    @patch('pubsub_logging.pubsub_handler.publish_body')
    def test_cut_buffer(self, publish_body):
        """Tests if we cut the buffer upon recoverale errors."""
        self.handler._buf_hard_limit = 0
        self.handler.emit(self.r)
        publish_body.side_effect = RecoverableError()
        self.handler.flush()

        publish_body.assert_called_once_with(
            self.mocked_client, self.expected_body, self.topic, self.RETRY)
        self.assertEqual(0, len(self.handler.buffer))
