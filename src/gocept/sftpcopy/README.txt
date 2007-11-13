========
SFTPCopy
========

Configure an sftpcopy:

>>> import tempfile
>>> import gocept.filestore
>>> import gocept.sftpcopy
>>> store_dir = tempfile.mkdtemp()
>>> filestore = gocept.filestore.FileStore(store_dir)
>>> filestore.prepare()
>>> sftp = gocept.sftpcopy.SFTPCopy(
...     'download', filestore,
...     'localhost', 22, 'testuser', 'dummy-password', 'in')

Connecting will not work because the user does not exist:

>>> sftp.connect()
Traceback (most recent call last):
    ...
AuthenticationException: Authentication failed.


For more tests we'll need to setup an sftp-server in the test case (via
paramiko probably).


Cleanup
=======

>>> import shutil
>>> shutil.rmtree(store_dir)

