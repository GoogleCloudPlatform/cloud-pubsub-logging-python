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

"""Python logging handler implementations for Cloud Pub/Sub.

Modules in this package send the logs to Cloud Pub/Sub[1]. The
pubsub_handler module has a sync version of the handler.

[1]: https://cloud.google.com/pubsub/docs

"""

import logging
import logging.handlers
import os
import sys

from .pubsub_handler import PubsubHandler  # flake8: noqa
from .async_handler import AsyncPubsubHandler  # flake8: noqa

__version__ = '0.2.1'
