# Copyright (c) 2006-2007 gocept gmbh & co. kg
# See also LICENSE.txt

import ConfigParser
import gocept.filestore
import logging
import os
import os.path
import paramiko
import sys


class SFTPCopy(object):

    def __init__(
        self, local_path, hostname, port, username, password, remote_path):
        self._transport = None
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.remote_path = remote_path
        self.filestore = gocept.filestore.FileStore(local_path)

    def connect(self):
        hostkey = self.getHostKey(self.hostname)

        url = 'sftp://%s:<hidden>@%s:%s/%s' % (
            self.username, self.hostname, self.port, self.remote_path)
        try:
            self._transport = paramiko.Transport((self.hostname, self.port))
            self._transport.connect(username=self.username,
                                    password=self.password,
                                    hostkey=hostkey)
            self.sftp = paramiko.SFTPClient.from_transport(self._transport)
            self.sftp.chdir(self.remote_path)
        except:
            logging.error('Error connecting to %s' % url, exc_info=True)
            raise
        else:
            logging.info('Connected to %s' % url)

    def close(self):
        logging.info('Disconnecting.')
        self._transport.close()
        self._transport = None

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

    def uploadFileContents(self, filename, data):
        remote = self.sftp.file(os.path.basename(filename), 'w')
        remote.write(data)
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


def main(configdict=sys.argv):
    config = configdict # keep parameter name backwards compatible
    if not isinstance(config, dict):
        # XXX tests for config file mode are missing, so it might not work at
        # all
        parser = ConfigParser.SafeConfigParser()
        parser.read(config[1])
        config = {}

        try:
            config['logfile'] = parser.get('general', 'logfile')
        except ConfigParser.NoOptionError:
            pass

        config['mode'] = parser.get('general', 'mode')
        config['local_path'] = parser.get('local', 'path')

        config['hostname'] = parser.get('remote', 'hostname')
        config['port'] = parser.getint('remote', 'port')
        config['username'] = parser.get('remote', 'username')
        config['password'] = parser.get('remote', 'password')
        config['remote_path'] = parser.get('remote', 'path')

    if config.get('logfile'):
        logfile = open(config.get('logfile'), 'a')
    else:
        logfile = sys.stdout
    configure_logging(stream=logfile, level=logging.INFO)

    filestore = gocept.filestore.FileStore(config['local_path'])
    filestore.prepare()
    cpy = SFTPCopy(config['local_path'],
                   config['hostname'], config.get('port', 22),
                   config['username'], config['password'],
                   config['remote_path'])
    cpy.connect()
    if config['mode'] == 'upload':
        cpy.uploadNewFiles()
    elif config['mode'] == 'download':
        cpy.downloadNewFiles()
    else:
        raise ValueError("Invalid parameter for general/mode")
    cpy.close()
