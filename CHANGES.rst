Changelog
=========

2.1 (2025-07-16)
================

- Add compatability to Python 3.11 and 3.12.


2.0 (2020-06-18)
================

Backward incompatible changes
-----------------------------

- Remove AMQP integration. If you need AMQP integration, stick to using a
  version < 1.0.

Other changes
-------------

- Add support for Python 3.7 and 3.8.

- Migrate to Github.

Info
----

- Version 1.0 was in internal release, so omitting it here.


0.6.0 (2016-11-02)
==================

- Pinning version numbers of dependencies for tests.

- Migrate to py.test as testrunner.

- Add new `skip_files` parameter to skip upload or download of files.


0.5.1 (2015-04-15)
==================

- Update `bootstrap.py` to version from ``zc.buildout 2.3.0``.

- Move repository to `bitbucket.org`.


0.5.0 (2014-11-26)
==================

- Set up keep-alive checking.


0.4.1 (2014-03-07)
==================

- Fixed brown-bag release.


0.4.0 (2014-03-07)
==================

- Copy files in chunks instead of loading each complete file into memory.
  There is a new config option ``buffer_size`` which defaults to 64 kB.


0.3.0 (2014-02-20)
==================

- Support key-based authentication.

- Check that the size of the transmitted file after up/download matches what
  was transferred.


0.2.2 (2012-04-04)
==================

- Update to gocept.amqprun-0.8.


0.2.1 (2012-03-29)
==================

- Make amqp server configurable for tests.
- Clean up garbage connections left by tests (#10634).


0.2 (2012-02-22)
================

- Add ``gocept.amqprun`` integration.


0.1.4 (2009-11-16)
==================

- Log errors that occur while connecting


0.1.3 (2008-02-27)
==================

- Added ``configdict`` argument to main function for easier buildout
  integration.


0.1.2 (2008-02-18)
==================

- Fixed bug in connection logging.
- Remember filestore so we can actually upload/download.
- Did some testing predefined user.


0.1.1 (2007-11-13)
==================

- Fixed brown back release 0.1 which was not usable at all since there were
  various files missing in the archive.
