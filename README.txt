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

You can either give the name of a configuration file on the commandline, or
pass the configuration values as a dict directly to the entrypoint (useful for
buildout integration). The configuration file has the following format::

    [general]
    mode = upload # or download
    logfile = /path/to/logfile # defaults to stdout if not given

    [local]
    path = /path/on/local/machine

    [remote]
    path = /path/on/remote/machine
    hostname = remote.host
    port = 22
    username = user
    password = secret

The configdict uses the following keys instead:

- logfile
- local_path
- remote_path
- hostname
- port
- username
- password

You can also use sftpcopy as a python object like this::

    import gocept.sftpcopy
    sftp = gocept.sftpcopy.SFTPCopy(
        'download', '/path/on/local/machine',
        'remote.host', 22, 'user', 'secret', '/path/on/remote/machine')
    sftp.connect()
    sftp.uploadNewFiles() # or sftp.downloadNewFiles()
