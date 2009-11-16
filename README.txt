========
SFTPCopy
========

sftpcopy allows to copy files to or from a remote server -- integrates with
gocept.filestore. sftpcopy will take files from the `new` directory, copy
them to the remote server and put them into `cur` on success. Likewise it will
download files from the remote server and put them into the `new` directory for
another application to pick it up.

All together this allows quite stable and asynchronous data transfer.

TODO
====

* Documentation
* Tests!
* Interfaces would be nice :)
