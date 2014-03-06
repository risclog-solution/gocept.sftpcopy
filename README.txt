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
    buffer_size = 65536

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
- buffer_size
- local_path
- remote_path
- hostname
- port
- username
- password
- key_filename

key_filename takes precedence over password. If key_filename ends with ``dsa``,
it's assumed to be a DSA key, else an RSA key. Note that the key file must not
be password protected.

buffer_size defaults to 65536. Files are copied in chunks of this size to
avoid loading big files into memory at once.

You can also use sftpcopy as a python object like this::

    import gocept.sftpcopy
    sftp = gocept.sftpcopy.SFTPCopy(
        '/path/on/local/machine',
        'remote.host', 22, 'user', 'secret', '/path/on/remote/machine')
    sftp.connect()
    sftp.uploadNewFiles() # or sftp.downloadNewFiles()


AMQP integration
================

If you require the `amqp` extra, gocept.sftpcopy offers a `gocept.amqprun`_
queue handler that uploads the message body as a file via SFTP (it respects the
``X-Filename`` header or generates a filename based on routing key and a
timestamp). Here's an example ZCML snippet::

    <configure xmlns="http://namespaces.zope.org/zope"
               xmlns:amqp="http://namespaces.gocept.com/amqp">

      <include package="gocept.amqprun" />
      <include package="gocept.sftpcopy" file="meta.zcml" />

      <amqp:sftpupload
        routing_key="test.data"
        queue_name="test.queue"
        hostname="remote.host"
        port="22"
        username="user"
        password="secret" [ALTERNATIVELY] key_filename="/path/to/private_key"
        remote_path="/path/on/remote/machine"
        arguments="
        x-ha-policy = all
        "
        />

    </configure>


.. _`gocept.amqprun`: http://pypi.python.org/pypi/gocept.amqprun
