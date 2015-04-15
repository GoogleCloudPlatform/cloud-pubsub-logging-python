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

"""A example script for Pub/Sub logging handlers."""

import argparse
import logging
import logging.config
import logging.handlers
import sys
import time

from pubsub_logging import AsyncPubsubHandler
from pubsub_logging import PubsubHandler


def main():
    parser = argparse.ArgumentParser(description='Testing AsyncPubsubHandler')
    parser.add_argument('-m', '--num_messages', metavar='N', type=int,
                        default=100000, help='number of messages')
    parser.add_argument('-w', '--num_workers', metavar='N', type=int,
                        default=20, help='number of workers')
    parser.add_argument('-t', '--timeout', metavar='D', type=float,
                        default=1, help='timeout for the BatchQueue.get')
    parser.add_argument('--async', dest='async', action='store_true')
    parser.add_argument('--no-async', dest='async', action='store_false')
    parser.set_defaults(async=True)
    parser.add_argument('--debug', dest='debug', action='store_true')
    parser.add_argument('--no-debug', dest='debug', action='store_false')
    parser.set_defaults(debug=False)
    parser.add_argument('topic', default='')
    args = parser.parse_args()
    num = args.num_messages
    workers = args.num_workers
    topic = args.topic
    if args.async:
        sys.stderr.write('Using AsyncPubsubHandler.\n')
        pubsub_handler = AsyncPubsubHandler(topic, workers,
                                            timeout=args.timeout,
                                            debug=args.debug)
    else:
        sys.stderr.write('Using PubsubHandler.\n')
        pubsub_handler = PubsubHandler(topic=topic, debug=args.debug)
    pubsub_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger('root')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(pubsub_handler)

    before = time.time()
    for i in range(num):
        logger.info('log message %03d.', i)
    elapsed = time.time() - before
    sys.stderr.write('Took %f secs for buffering %d messages: %f mps.\n' %
                     (elapsed, num, num/elapsed))
    pubsub_handler.flush()
    elapsed = time.time() - before
    sys.stderr.write('Took %f secs for sending %d messages: %f mps.\n' %
                     (elapsed, num, num/elapsed))


if __name__ == '__main__':
    main()
