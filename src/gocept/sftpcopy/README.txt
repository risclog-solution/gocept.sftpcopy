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
...     'localhost', 22, 'test', 'D>Mx,62I', 'tmp')


After connecting ...

>>> sftp.connect()

... we can download ...

>>> sftp.copyNewFiles()

... and upload files ...

>>> sftp.uploadNewFiles()

Those methods doe not put anything out if there is no error.


Cleanup
=======

>>> sftp.close()
>>> import shutil
>>> shutil.rmtree(store_dir)

