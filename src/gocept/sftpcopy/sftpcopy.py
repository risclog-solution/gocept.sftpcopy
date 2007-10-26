# Copyright (c) 2006-2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import os
import os.path
import sys
import logging
import ConfigParser

import paramiko

import gocept.filestore


class SFTPCopy(object):

    def __init__(self, mode, filestore,
                 hostname, port, username, password, remote_path):
        self._transport = None
        if mode not in ('upload', 'download'):
            raise ValueError("`upload` must bei 'upload' or 'download'")
        self.mode = mode
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.remote_path = remote_path

    def connect(self):
        hostkey = self.getHostKey(self.hostname)

        self._transport = paramiko.Transport((self.hostname, self.port))
        self._transport.connect(username=self.username,
                                password=self.password,
                                hostkey=hostkey)
        self.sftp = paramiko.SFTPClient.from_transport(self._transport)
        self.sftp.chdir(self.remote_path)

        logging.info('Connected to sftp://%s:<hidden>@%s:%s/%s' % (
            self.username, self.hostname, self.port, self.path))

    def close(self):
        logging.info('Disconnecting.')
        self._transport.close()
        self._transport = None

    def copyNewFiles(self):
        if self.mode == 'upload':
            self.uploadNewFiles()
        elif self.mode == 'download':
            self.downloadNewFiles()
        else:
            raise ValueError("Invalid parameter for general/mode")

    def uploadNewFiles(self):
        for filename in self.filestore.list('new'):
            basename = os.path.basename(filename)
            try:
                self.uploadFile(filename)
            except IOError, e:
                logging.error('Failed to upload %s (IOError: %s)' % (basename,
                                                                     e))
            else:
                self.filestore.move(filename, 'new', 'cur')
                logging.info('Uploaded %s' % basename)

    def uploadFile(self, filename):
        basename = os.path.basename(filename)
        sftp = self.sftp

        local = file(filename, 'rb')
        remote = sftp.file(basename, 'w')

        data = local.read()
        remote.write(data)

        local.close()
        remote.close()

    def downloadNewFiles(self):
        sftp = self.sftp
        filestore = self.filestore
        for name in sftp.listdir():
            try:
                remote = sftp.file(name, 'r')
                local = filestore.create(name)

                data = remote.read()
                local.write(data)

                remote.close()
                local.close()

                filestore.move(name, 'tmp', 'new')
                logging.info('Downloaded %s' % name)

                sftp.unlink(name)
                logging.info('Removed remote file %s' % name)
            except IOError, e:
                logging.error('Failed to download %r (IOError: %s)' % (
                    name, e))


    def getHostKey(self, hostname):
        hostkey = None
        try:
            host_keys = paramiko.util.load_host_keys(
                os.path.expanduser('~/.ssh/known_hosts'))
        except IOError:
            host_keys = {}
        keys = host_keys.get(hostname)
        if keys is None:
            host_key = None
        else:
            host_key = host_keys.get('ssh-dss')
        return host_key


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"


def configure_logging(filename=None, filemode=None, stream=None,
                      format=LOG_FORMAT, dateformat=None, level=None):
    if len(logging.root.handlers) == 0:
        if filename:
            hdlr = logging.FileHandler(filename, filemode)
        else:
            hdlr = logging.StreamHandler(stream)
        fmt = logging.Formatter(format, dateformat)
        hdlr.setFormatter(fmt)
        logging.root.addHandler(hdlr)
        if level:
            logging.root.setLevel(level)


def main(configfile=None):
    """Console script to copy things defined by config file."""
    config = ConfigParser.SafeConfigParser()
    if configfile is None:
        # TODO: use getopt
        configfile = sys.argv[1]
    config.read(configfile)

    try:
        logfile_name = config.get('general', 'logfile')
    except ConfigParser.NoOptionError:
        logfile = sys.stdout
    else:
        logfile = file(logfile_name, 'a')

    configure_logging(stream=logfile, level=logging.INFO)

    mode = config.get('general', 'mode')
    filestore = gocept.filestore.FileStore(config.get('local', 'path'))
    filestore.prepare()

    hostname = config.get('remote', 'hostname')
    port = config.getint('remote', 'port')
    username = config.get('remote', 'username')
    password = config.get('remote', 'password')
    path = config.get('remote', 'path')

    cpy = SFTPCopy(mode, filestore,
                   hostname, port, username, password, path)
    cpy.connect()
    cpy.copyNewFiles()
    cpy.close()
