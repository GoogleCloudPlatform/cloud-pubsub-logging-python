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
import unittest

from apiclient import errors
import mock

import pubsub_logging


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


class FlushTest(unittest.TestCase):
    """Tests for the flush method."""
    RETRY = 3
    BATCH_NUM = 2

    def setUp(self):
        self.mocked_client = mock.MagicMock()
        self.topic = 'projects/test-project/topics/test-topic'
        self.handler = pubsub_logging.PubsubHandler(
            topic=self.topic, client=self.mocked_client, retry=self.RETRY,
            capacity=self.BATCH_NUM)
        self.projects = self.mocked_client.projects.return_value
        self.topics = self.projects.topics.return_value
        self.topics_publish = self.topics.publish.return_value
        self.log_msg = 'Test message'
        self.expected_payload = pubsub_logging.compat_urlsafe_b64encode(
            self.log_msg)
        self.expected_body = {'messages': [{'data': self.expected_payload}]}
        self.r = logging.LogRecord('test', logging.INFO, None, 0, self.log_msg,
                                   [], None)

    def test_flush(self):
        """Tests if the flush method calls Pub/Sub API."""
        self.handler.emit(self.r)

        self.handler.flush()

        self.topics.publish.assert_called_once_with(
            topic=self.topic, body=self.expected_body)
        self.topics_publish.execute.assert_called_with(num_retries=self.RETRY)
        self.assertEqual(0, len(self.handler.buffer))

    def test_flush_raise_on_publish_404(self):
        """Tests if the flush method raises when publish gets a 404 error."""
        self.handler.emit(self.r)
        mocked_resp = mock.MagicMock()
        mocked_resp.status = 404
        mocked_resp.reason = 'Not Found'
        # 404 error with the second side effect for flushing at exit.
        self.topics_publish.execute.side_effect = [
            errors.HttpError(mocked_resp, 'Not found'),
            ['msgid1']
        ]
        self.assertRaises(errors.HttpError, self.handler.flush)

    def test_flush_raise_on_publish_403(self):
        """Tests if the flush method raises when publish gets a 403 error."""
        self.handler.emit(self.r)
        mocked_resp = mock.MagicMock()
        mocked_resp.status = 403
        mocked_resp.reason = 'Access not allowed'
        # 403 error with the second side effect for flushing at exit.
        self.topics_publish.execute.side_effect = [
            errors.HttpError(mocked_resp, 'Access not allowed'),
            ['msgid1']
        ]
        self.assertRaises(errors.HttpError, self.handler.flush)

    def test_flush_ignore_recoverable(self):
        """Tests if we ignore 503 error from Cloud Pub/Sub."""
        self.handler.emit(self.r)
        mocked_resp = mock.MagicMock()
        mocked_resp.status = 503
        mocked_resp.reason = 'Server Error'
        # 503 error, with the second side effect for flushing at exit.
        self.topics_publish.execute.side_effect = [
            errors.HttpError(mocked_resp, 'Server Error'),
            ['msgid1']
        ]
        self.handler.flush()

        self.topics.publish.assert_called_once_with(
            topic=self.topic, body=self.expected_body)
        self.topics_publish.execute.assert_called_once_with(
            num_retries=self.RETRY)
        self.assertEqual(1, len(self.handler.buffer))

    def test_cut_buffer(self):
        """Tests if we cut the buffer upon recoverale errors."""
        self.handler._buf_hard_limit = 0
        self.handler.emit(self.r)
        mocked_resp = mock.MagicMock()
        mocked_resp.status = 503
        mocked_resp.reason = 'Server Error'
        # 503 error, with the second side effect for flushing at exit.
        self.topics_publish.execute.side_effect = [
            errors.HttpError(mocked_resp, 'Server Error'),
            ['msgid1']
        ]
        self.handler.flush()

        self.topics.publish.assert_called_once_with(
            topic=self.topic, body=self.expected_body)
        self.topics_publish.execute.assert_called_once_with(
            num_retries=self.RETRY)
        self.assertEqual(0, len(self.handler.buffer))
