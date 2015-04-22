Contributor License Agreements
------------------------------

Before we can accept your pull requests you'll need to sign a Contributor License Agreement (CLA):

* If you are an individual writing original source code and you own the intellectual property, then you'll need to sign an [individual CLA](https://developers.google.com/open-source/cla/individual).

* If you work for a company that wants to allow you to contribute your work, then you'll need to sign a [corporate CLA](https://developers.google.com/open-source/cla/corporate>).

You can sign these electronically (just scroll to the bottom). After that, we'll be able to accept your pull requests.

Travis test
===========

Unfortunately, the tests depend on the travis secret variables for
decrypting the json key, and the secret variables are not available
for pull requests from other repos.

So if you want to create a pull request, consider creating a pull
request to the `contribution` branch first. We'll review the pull
requests then merge to the `contribution`. After that we'll be able to
run the travis tests with another pull request from `contribution` to
`master` branch.

Run the tests
=============

Before sending a pull request, consider running the tests. To run the
tests, follow the instructions below.

* Install tox

  $ pip install tox

* Create a Cloud Project if you don't have it.
* Create a service account if you don't have it.
* Download a JSON key of that service account.
* Set environment variable

  * GOOGLE_APPLICATION_CREDENTIALS: the file name of the JSON key
  * PUBSUB_LOGGING_TEST_PROJECT: your project id

* Run tox

Note: Don't submit your JSON key!!
