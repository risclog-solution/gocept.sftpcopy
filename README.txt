========
SFTPCopy
========

sftpcopy allows to copy files to or from a remote server -- integrates with
gocept.filestore. sftpcopy will take files from the `new` directory, copy
them to the remote server and put them into `cur` on success. Likewise it will
download files from the remote server and put them into the `new` directory for
another application to pick it up.

Usage
=====

::

    import gocept.filestore
    import gocept.sftpcopy
    filestore = gocept.filestore.FileStore(store_dir)
    filestore.prepare()
    sftp = gocept.sftpcopy.SFTPCopy(
        'download', '/path/on/local/machine',
        'remote.host', 22, 'user', 'password', '/path/on/remote/machine')
    sftp.connect()
    sftp.uploadNewFiles()
    sftp.downloadNewFiles()
