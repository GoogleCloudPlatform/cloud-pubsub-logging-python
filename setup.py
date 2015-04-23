from __future__ import with_statement

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

pubsub_logging_classifiers = [
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 3',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Topic :: Software Development :: Libraries',
    'Topic :: Utilities',
]

with open('README.rst', 'r') as fp:
    pubsub_logging_long_description = fp.read()

REQUIREMENTS = [
    'google-api-python-client >= 1.4.0'
]

setup(
    name='pubsub-logging',
    version='0.2.1',
    author='Takashi Matsuo',
    author_email='tmatsuo@google.com',
    url='https://github.com/GoogleCloudPlatform/cloud-pubsub-logging-python',
    packages=['pubsub_logging'],
    description="Logging handlers for publishing the logs to Cloud Pub/Sub",
    install_requires=REQUIREMENTS,
    long_description=pubsub_logging_long_description,
    license='Apache 2.0',
    classifiers=pubsub_logging_classifiers
)
