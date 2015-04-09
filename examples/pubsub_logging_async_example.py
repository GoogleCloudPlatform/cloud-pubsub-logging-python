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

"""A example script for Pub/Sub async logging handler."""

import logging
import logging.config
import logging.handlers
import os
import sys

from pubsub_logging import AsyncPubsubHandler


def main():
    logger = None
    if len(sys.argv) == 2:
        topic = sys.argv[1]
        pubsub_handler = AsyncPubsubHandler(topic, 10)
        pubsub_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

        logger = logging.getLogger('root')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(pubsub_handler)
    else:
        logging.config.fileConfig(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)), 'async.conf'))
        logger = logging.getLogger('root')
    for i in range(100):
        logger.info('log message %03d.', i)


if __name__ == '__main__':
    main()
