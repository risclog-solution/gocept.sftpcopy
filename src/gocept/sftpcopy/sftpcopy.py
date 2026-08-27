# Copyright (c) 2006-2014 gocept gmbh & co. kg
# See also LICENSE.txt

import configparser
import gocept.filestore
import logging
import os
import os.path
import paramiko
import socket
import sys
import time


class RemoteFileChangedError(IOError):
    """Raised when a partially downloaded remote file was modified before
    the download could be resumed."""


class SFTPCopy(object):
    # Exceptions that plausibly indicate a lost connection (as opposed to,
    # e.g., "file not found" or "permission denied") and therefore warrant
    # a reconnect/resume attempt during downloads.
    RECONNECT_EXCEPTIONS = (
        paramiko.SSHException,
        EOFError,
        socket.timeout,
        ConnectionError,
    )

    def __init__(
        self,
        local_path,
        hostname,
        port,
        username,
        password,
        remote_path,
        key_filename=None,
        buffer_size=None,
        skip_files=None,
        keepalive_interval=5,
        reconnect_attempts=3,
        reconnect_delay=1,
    ):
        self._transport = None
        self.hostname = hostname
        self.port = port
        self.username = username
        self.skip_files = [] if skip_files is None else skip_files
        self.password = password
        self.key_filename = key_filename
        self.remote_path = remote_path
        self.filestore = gocept.filestore.FileStore(local_path)
        self.buffer_size = buffer_size or 64 * 1024
        self.keepalive_interval = keepalive_interval
        self.reconnect_attempts = int(reconnect_attempts)
        self.reconnect_delay = float(reconnect_delay) if reconnect_delay else 0

    def connect(self):
        hostkey = self.getHostKey(self.hostname)

        url = "sftp://{}:<hidden>@{}:{}/{}".format(
            self.username, self.hostname, self.port, self.remote_path
        )
        try:
            self._transport = paramiko.Transport((self.hostname, self.port))
            self._transport.set_keepalive(self.keepalive_interval)
            connect_args = {
                "username": self.username,
                "hostkey": hostkey,
            }
            if self.key_filename:
                ext = self.key_filename[:-3]
                if ext == "dsa":
                    key_class = paramiko.DSSKey
                else:
                    key_class = paramiko.RSAKey
                connect_args["pkey"] = key_class.from_private_key_file(
                    self.key_filename
                )
            else:
                connect_args["password"] = self.password
            self._transport.connect(**connect_args)
            self.sftp = paramiko.SFTPClient.from_transport(self._transport)
            self.sftp.chdir(self.remote_path)
        except Exception:
            logging.error("Error connecting to %s" % url, exc_info=True)
            raise
        else:
            logging.info("Connected to %s" % url)

    def close(self):
        logging.info("Disconnecting.")
        if self._transport is not None:
            try:
                self._transport.close()
            except Exception:
                # The transport may already have been torn down by the
                # server, e.g. after a dropped connection.
                logging.warning("Error while closing transport", exc_info=True)
        self._transport = None

    def _reconnect(self):
        self.close()
        if self.reconnect_delay:
            time.sleep(self.reconnect_delay)
        self.connect()

    def uploadNewFiles(self):
        for filename in self.filestore.list("new"):
            if os.path.basename(filename) in self.skip_files:
                continue
            basename = os.path.basename(filename)
            try:
                self.uploadFile(filename)
            except IOError as e:
                logging.error("Failed to upload {} (IOError: {})".format(basename, e))
            else:
                self.filestore.move(filename, "new", "cur")
                logging.info("Uploaded %s" % basename)

    def uploadFile(self, filename):
        basename = os.path.basename(filename)
        sftp = self.sftp

        local = open(filename, "rb")
        remote = sftp.file(basename, "w")

        size = self._copy_file(local, remote)

        local.close()
        remote.close()
        self._check_remote_filesize(basename, size)

    def uploadFileContents(self, filename, data):
        basename = os.path.basename(filename)
        remote = self.sftp.file(basename, "w")
        remote.write(data)
        remote.close()
        self._check_remote_filesize(basename, len(data))

    def _check_remote_filesize(self, filename, size):
        stat = self.sftp.stat(filename)
        if stat.st_size != size:
            raise IOError(
                "Transmitted %s bytes to %r, but %s arrived"
                % (size, filename, stat.st_size)
            )

    def downloadNewFiles(self):
        sftp = self.sftp
        filestore = self.filestore
        for name in sftp.listdir():
            try:
                if name in self.skip_files:
                    continue
                local = filestore.create(name, mode="wb")
                try:
                    size = self._download_file(name, local)
                finally:
                    local.close()
                self._check_local_filesize(name, size)

                filestore.move(name, "tmp", "new")
                logging.info("Downloaded %s" % name)

                self.sftp.unlink(name)
                logging.info("Removed remote file %s" % name)
            except IOError as e:
                logging.error("Failed to download {!r} (IOError: {})".format(name, e))
            except self.RECONNECT_EXCEPTIONS as e:
                # Surfaces once the reconnect attempts for this file have
                # been exhausted; logged and skipped like any other
                # per-file download failure.
                logging.error(
                    "Failed to download {!r} ({}: {})".format(name, type(e).__name__, e)
                )

    def _stat_remote_file(self, name):
        stat = self.sftp.stat(name)
        return stat.st_size, getattr(stat, "st_mtime", None)

    def _download_file(self, name, local):
        """Download `name` into the already opened local file `local`,
        transparently reconnecting and resuming at the last successfully
        written byte if the connection drops while reading.
        """
        remote_size, remote_mtime = self._stat_remote_file(name)
        remote = self.sftp.file(name, "r")
        offset = 0
        attempt = 0
        while True:
            try:
                while True:
                    data = remote.read(int(self.buffer_size))
                    if not data:
                        return offset
                    # Local write failures (e.g. disk full) are not
                    # connection problems and must not trigger a reconnect.
                    local.write(data)
                    offset += len(data)
            except self.RECONNECT_EXCEPTIONS:
                if attempt >= self.reconnect_attempts:
                    logging.error(
                        "Unable to resume download of %r after %s "
                        "reconnect attempts." % (name, self.reconnect_attempts)
                    )
                    raise
                attempt += 1
                logging.warning(
                    "Connection dropped while downloading %r after %s "
                    "bytes." % (name, offset)
                )
                logging.info(
                    "Reconnecting (attempt {}/{}).".format(
                        attempt, self.reconnect_attempts
                    )
                )
                remote = self._resume_remote_file(
                    name, offset, remote_size, remote_mtime
                )

    def _resume_remote_file(self, name, offset, remote_size, remote_mtime):
        self._reconnect()
        new_size, new_mtime = self._stat_remote_file(name)
        if (
            new_size != remote_size
            or offset > new_size
            or (
                remote_mtime is not None
                and new_mtime is not None
                and new_mtime != remote_mtime
            )
        ):
            raise RemoteFileChangedError(
                "Remote file %r changed while downloading; refusing to " "resume" % name
            )
        remote = self.sftp.file(name, "r")
        remote.seek(offset)
        logging.info("Resuming download of {!r} at byte {}.".format(name, offset))
        return remote

    def _copy_file(self, source, target):
        size = 0
        while True:
            data = source.read(int(self.buffer_size))
            if not data:
                break
            target.write(data)
            size += len(data)
        return size

    def _check_local_filesize(self, filename, size):
        filename = os.path.join(self.filestore.path, "tmp", filename)
        stat = os.stat(filename)
        if stat.st_size != size:
            raise IOError(
                "Transmitted %s bytes to %r, but %s arrived"
                % (size, filename, stat.st_size)
            )

    def getHostKey(self, hostname):
        try:
            host_keys = paramiko.util.load_host_keys(
                os.path.expanduser("~/.ssh/known_hosts")
            )
        except IOError:
            host_keys = {}
        keys = host_keys.get(hostname)
        if keys is None:
            host_key = None
        else:
            host_key = host_keys.get("ssh-dss")
        return host_key


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"


def configure_logging(
    filename=None,
    filemode=None,
    stream=None,
    format=LOG_FORMAT,
    dateformat=None,
    level=None,
):
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
    config = configdict  # keep parameter name backwards compatible
    if not isinstance(config, dict):
        # XXX tests for config file mode are missing, so it might not work at
        # all
        if len(config) > 1:
            config_file_name = config[1]
        else:
            config_file_name = "sftpcopy.ini"
        parser = configparser.ConfigParser()
        parser.read(config_file_name)
        config = {}

        try:
            config["logfile"] = parser.get("general", "logfile")
        except configparser.NoOptionError:
            pass

        config["mode"] = parser.get("general", "mode")
        config["buffer_size"] = parser.get("general", "buffer_size")
        config["skip_files"] = parser.get("general", "skip_files")
        config["keepalive_interval"] = parser.get("general", "keepalive_interval")
        try:
            config["reconnect_attempts"] = parser.get("general", "reconnect_attempts")
        except configparser.NoOptionError:
            pass
        try:
            config["reconnect_delay"] = parser.get("general", "reconnect_delay")
        except configparser.NoOptionError:
            pass
        config["local_path"] = parser.get("local", "path")

        config["hostname"] = parser.get("remote", "hostname")
        config["port"] = parser.getint("remote", "port")
        config["username"] = parser.get("remote", "username")
        config["password"] = parser.get("remote", "password")
        config["remote_path"] = parser.get("remote", "path")

    VALID_KEYS = {
        "logfile",
        "mode",
        "local_path",
        "hostname",
        "port",
        "username",
        "password",
        "remote_path",
        "buffer_size",
        "keepalive_interval",
        "skip_files",
        "reconnect_attempts",
        "reconnect_delay",
    }
    for key in config.keys():
        if key not in VALID_KEYS:
            raise ValueError("Invalid configuration key %r" % key)

    if config.get("logfile"):
        logfile = open(config.get("logfile"), "a")
    else:
        logfile = sys.stdout
    configure_logging(stream=logfile, level=logging.INFO)

    filestore = gocept.filestore.FileStore(config["local_path"])
    filestore.prepare()
    cpy = SFTPCopy(
        config["local_path"],
        config["hostname"],
        config.get("port", 22),
        config["username"],
        config["password"],
        config["remote_path"],
        buffer_size=config.get("buffer_size"),
        skip_files=config.get("skip_files"),
        reconnect_attempts=config.get("reconnect_attempts", 3),
        reconnect_delay=config.get("reconnect_delay", 1),
    )
    cpy.connect()
    if config["mode"] == "upload":
        cpy.uploadNewFiles()
    elif config["mode"] == "download":
        cpy.downloadNewFiles()
    else:
        raise ValueError("Invalid parameter for general/mode")
    cpy.close()
