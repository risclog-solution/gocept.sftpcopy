========
SFTPCopy
========

sftpcopy allows to copy files to or from a remote server -- integrates with
`gocept.filestore <https://pypi.org/project/gocept.filestore/>`_.
sftpcopy will take files from the ``new`` directory, copy
them to the remote server and put them into ``cur`` on success. Likewise it will
download files from the remote server and put them into the ``new``
directory for another application to pick it up.

Usage
=====

You can either give the name of a configuration file on the commandline, or
pass the configuration values as a dict directly to the entrypoint (useful for
buildout integration). The configuration file has the following format::

    [general]
    mode = upload # or download
    logfile = /path/to/logfile # defaults to stdout if not given
    buffer_size = 65536
    skip_files =
        name_of_file_to_skip_1
        name_of_file_to_skip_2

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
- buffer_size (default: 65536, i.e. 64 KiB)
- keepalive_interval (default: 5 seconds)
- local_path
- remote_path
- hostname
- port
- username
- password
- key_filename
- skip_files

key_filename takes precedence over password. If key_filename ends with ``dsa``,
it's assumed to be a DSA key, else an RSA key. Note that the key file must not
be password protected.

``skip_files`` is a list of filenames (local or remote), which are skipped during
upload or download.

Files are copied in chunks of buffer_size to avoid loading big files into
memory at once.

You can also use sftpcopy as a python object like this::

    import gocept.sftpcopy
    sftp = gocept.sftpcopy.SFTPCopy(
        '/path/on/local/machine',
        'remote.host', 22, 'user', 'secret', '/path/on/remote/machine',
        skip_files=['my_file_to_ignore'])
    sftp.connect()
    sftp.uploadNewFiles()  # or sftp.downloadNewFiles()
