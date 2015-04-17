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

"""Utilities for the Python logging handlers."""


import base64
import sys
import threading

from googleapiclient import discovery
from googleapiclient import errors

import httplib2

from oauth2client.client import GoogleCredentials

from pubsub_logging.errors import RecoverableError


PUBSUB_SCOPES = ["https://www.googleapis.com/auth/pubsub"]

clients = threading.local()


def compat_urlsafe_b64encode(v):
    """A urlsafe ba64encode which is compatible with Python 2 and 3.

    Args:
      v: A string to encode.
    Returns:
      The encoded string.
    """
    if sys.version_info[0] >= 3:  # pragma: NO COVER
        return base64.urlsafe_b64encode(v.encode('UTF-8')).decode('ascii')
    else:
        return base64.urlsafe_b64encode(v)


def get_pubsub_client(http=None):  # pragma: NO COVER
    """Return a thread local Pub/Sub client.

    Args:
      http: httplib2.Http instance. Defaults to None.
    Returns:
      Cloud Pub/Sub client.
    """
    if not hasattr(clients, 'client'):
        credentials = GoogleCredentials.get_application_default()
        if credentials.create_scoped_required():
            credentials = credentials.create_scoped(PUBSUB_SCOPES)
        if not http:
            http = httplib2.Http()
        credentials.authorize(http=http)
        clients.client = discovery.build('pubsub', 'v1beta2', http=http)
    return clients.client


def publish_body(client, body, topic, retry):
    """Publishes the specified body to Cloud Pub/Sub.

    Args:
      client: Cloud Pub/Sub client.
      body: Post body for Pub/Sub publish call.
      topic: topic name that we publish the records to.
      retry: number of retry upon intermittent failures.

    Raises:
      errors.HttpError When the Cloud Pub/Sub API call fails with
                       unrecoverable reasons.
      RecoverableError When the Cloud Pub/Sub API call fails with
                       intermittent errors.
    """
    try:
        client.projects().topics().publish(
            topic=topic, body=body).execute(num_retries=retry)
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
