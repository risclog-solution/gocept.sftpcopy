========
SFTPCopy
========

sftpcopy allows to copy files to or from a remote server -- integrates with
gocept.filestore. sftpcopy will take files from the `new` directory, copy
them to the remote server and put them into `cur` on success. Likewise it will
download files from the remote server and put them into the `new` directory for
another application to pick it up.

All together this allows quite stable and asynchronous data transfer.

Changes
=======

0.1.3 (2008-02-27)
++++++++++++++++++

* Added `configdict` argument to main function for easier buildout integration.

0.1.2 (2008-02-18)
++++++++++++++++++

* Fixed bug in connection logging.
* Remember filestore so we can actually upload/download.
* Did some testing predefined user.


0.1.1 (2007-11-13)
++++++++++++++++++

* Fixed brown back release 0.1 which was not usable at all since there were
  various files missing in the archive.

TODO
====

* Documentation
* Tests!
* Interfaces would be nice :)
