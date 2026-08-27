# Copyright (c) 2012-2014 gocept gmbh & co. kg
# See also LICENSE.txt

import gocept.sftpcopy.sftpcopy
import gocept.sftpcopy.testing
import os
import os.path
import paramiko
import shutil
import tempfile
import unittest


class DropSchedule:
    """Shared, mutable state used by `DroppingFile`/`DroppingSFTP`/
    `FlakySFTPCopy` to deterministically simulate a lost SSH connection --
    while reading a remote file, while premature EOF is signalled, or
    while reconnecting itself -- regardless of how often the connection
    has already been re-established in the meantime.
    """

    def __init__(
        self,
        drop_after_bytes=(),
        exception_factory=None,
        on_drop=None,
        premature_eof_after_bytes=None,
        reconnect_failures=0,
    ):
        # Byte offsets (relative to the whole download) at which a
        # connection drop should be simulated. Consumed one at a time.
        self.pending = list(drop_after_bytes)
        self.total_read = 0
        self.seek_offsets = []
        self.exception_factory = exception_factory or (
            lambda: paramiko.SSHException("Server connection dropped")
        )
        self.on_drop = on_drop
        # Number of bytes after which a single read() should return an
        # empty result (simulated premature EOF) without actually having
        # reached the end of the file. Triggers only once.
        self.premature_eof_after_bytes = premature_eof_after_bytes
        self._premature_eof_triggered = False
        # Number of times `connect()`/reconnect should fail (raising a
        # simulated connection error) before actually succeeding.
        self.reconnect_failures = reconnect_failures


class DroppingFile:
    """Wraps a real `paramiko.SFTPFile` opened for reading and raises a
    simulated connection error (or signals a premature EOF) once the
    configured number of bytes has been read.
    """

    def __init__(self, real_file, schedule):
        self._real = real_file
        self._schedule = schedule

    def __getattr__(self, name):
        return getattr(self._real, name)

    def read(self, size=-1):
        schedule = self._schedule
        if schedule.pending and schedule.total_read >= schedule.pending[0]:
            schedule.pending.pop(0)
            if schedule.on_drop:
                schedule.on_drop()
            raise schedule.exception_factory()
        if (
            schedule.premature_eof_after_bytes is not None
            and not schedule._premature_eof_triggered
            and schedule.total_read >= schedule.premature_eof_after_bytes
        ):
            schedule._premature_eof_triggered = True
            return b""
        data = self._real.read(size)
        schedule.total_read += len(data)
        return data

    def seek(self, offset):
        self._schedule.seek_offsets.append(offset)
        return self._real.seek(offset)


class DroppingSFTP:
    """Wraps a real `paramiko.SFTPClient` so that files opened for reading
    are wrapped in a `DroppingFile`.
    """

    def __init__(self, real_sftp, schedule):
        self._real = real_sftp
        self._schedule = schedule

    def __getattr__(self, name):
        return getattr(self._real, name)

    def file(self, name, mode="r"):
        f = self._real.file(name, mode)
        if mode == "r":
            return DroppingFile(f, self._schedule)
        return f


class FlakySFTPCopy(gocept.sftpcopy.sftpcopy.SFTPCopy):
    """`SFTPCopy` that wraps the real sftp client with a `DroppingSFTP`
    test double after every (re-)connect, so connection drops can be
    simulated deterministically without any real network interruption.
    Can also simulate the reconnect itself failing a configurable number
    of times before succeeding.
    """

    def __init__(self, *args, **kw):
        self.drop_schedule = kw.pop("drop_schedule")
        super().__init__(*args, **kw)
        # Number of connect() calls that actually succeeded.
        self.connect_count = 0
        # Number of connect() calls attempted, including failed ones.
        self.connect_attempts = 0

    def connect(self):
        self.connect_attempts += 1
        schedule = self.drop_schedule
        if self.connect_attempts > 1 and schedule.reconnect_failures > 0:
            schedule.reconnect_failures -= 1
            raise paramiko.SSHException(
                "Server connection dropped (simulated reconnect failure)"
            )
        super().connect()
        self.connect_count += 1
        self.sftp = DroppingSFTP(self.sftp, schedule)


class EndToEndTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        server_dir = os.path.join(self.tmpdir, "server")
        os.mkdir(server_dir)
        self.sftp = gocept.sftpcopy.testing.SFTPThread(server_dir)
        self.sftp.start()

        self.config = dict(
            local_path=self.tmpdir,
            remote_path="/",
            hostname="localhost",
            port=self.sftp.port,
            username="user",
            password="secret",
        )

    def tearDown(self):
        self.sftp.stop()
        shutil.rmtree(self.tmpdir)

    def test_upload(self):
        os.mkdir(os.path.join(self.tmpdir, "new"))
        f = open(os.path.join(self.tmpdir, "new", "foo"), "w")
        f.write("contents")
        f.close()
        f = open(os.path.join(self.tmpdir, "new", "ignore"), "w").close()

        self.config["mode"] = "upload"
        self.config["buffer_size"] = 3
        self.config["skip_files"] = ["ignore"]
        gocept.sftpcopy.sftpcopy.main(self.config)

        uploaded = os.path.join(self.tmpdir, "server", "foo")
        self.assertTrue(os.path.isfile(uploaded))
        self.assertEqual("contents", open(uploaded).read())

        # 1 file was not copied
        self.assertEqual(1, len(os.listdir(os.path.join(self.tmpdir, "new"))))
        # 1 file was copied
        self.assertEqual(1, len(os.listdir(os.path.join(self.tmpdir, "cur"))))

    def test_download(self):
        f = open(os.path.join(self.tmpdir, "server", "foo"), "w")
        f.write("contents")
        f.close()
        f = open(os.path.join(self.tmpdir, "server", "ignore"), "w").close()

        self.config["mode"] = "download"
        self.config["buffer_size"] = 3
        self.config["skip_files"] = ["ignore"]
        gocept.sftpcopy.sftpcopy.main(self.config)

        downloaded = os.path.join(self.tmpdir, "new", "foo")
        self.assertTrue(os.path.isfile(downloaded))
        self.assertEqual("contents", open(downloaded).read())

        ignored = os.path.join(self.tmpdir, "new", "ignore")
        self.assertFalse(os.path.isfile(ignored))

        # 1 file was not copied
        self.assertEqual(1, len(os.listdir(os.path.join(self.tmpdir, "server"))))


class ConfigurationTest(unittest.TestCase):
    def test_invalid_config_key_should_raise(self):
        self.assertRaises(ValueError, gocept.sftpcopy.sftpcopy.main, dict(invalid=None))


class ReconnectResumeTest(unittest.TestCase):
    """Tests for automatic reconnect/resume of interrupted downloads."""

    CONTENTS = bytes(range(256)) * 4  # 1024 bytes, easy to spot corruption

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.server_dir = os.path.join(self.tmpdir, "server")
        os.mkdir(self.server_dir)
        self.sftp = gocept.sftpcopy.testing.SFTPThread(self.server_dir)
        self.sftp.start()
        self.remote_name = "foo.dat"
        self.remote_file = os.path.join(self.server_dir, self.remote_name)
        with open(self.remote_file, "wb") as f:
            f.write(self.CONTENTS)

    def tearDown(self):
        self.sftp.stop()
        shutil.rmtree(self.tmpdir)

    def make_copy(self, drop_schedule, buffer_size=3, **kw):
        cpy = FlakySFTPCopy(
            self.tmpdir,
            "localhost",
            self.sftp.port,
            "user",
            "secret",
            "/",
            buffer_size=buffer_size,
            drop_schedule=drop_schedule,
            **kw,
        )
        cpy.filestore.prepare()
        return cpy

    def downloaded_path(self):
        return os.path.join(self.tmpdir, "new", self.remote_name)

    def tmp_path(self):
        return os.path.join(self.tmpdir, "tmp", self.remote_name)

    def test_normal_download_without_drop_is_unaffected(self):
        cpy = self.make_copy(DropSchedule())
        cpy.connect()
        cpy.downloadNewFiles()
        cpy.close()

        self.assertEqual(1, cpy.connect_count)
        self.assertEqual(self.CONTENTS, open(self.downloaded_path(), "rb").read())
        self.assertFalse(os.path.exists(self.remote_file))

    def test_connection_drop_resumes_and_completes_download(self):
        schedule = DropSchedule(drop_after_bytes=[216])
        cpy = self.make_copy(schedule)
        cpy.connect()
        cpy.downloadNewFiles()
        cpy.close()

        # initial connection + one reconnect
        self.assertEqual(2, cpy.connect_count)
        self.assertEqual(self.CONTENTS, open(self.downloaded_path(), "rb").read())
        self.assertFalse(os.path.exists(self.remote_file))

    def test_resume_starts_at_correct_offset(self):
        schedule = DropSchedule(drop_after_bytes=[216])
        cpy = self.make_copy(schedule)
        cpy.connect()
        cpy.downloadNewFiles()
        cpy.close()

        self.assertEqual([216], schedule.seek_offsets)

    def test_multiple_connection_drops_are_all_resumed(self):
        schedule = DropSchedule(drop_after_bytes=[99, 300, 600])
        cpy = self.make_copy(schedule, reconnect_attempts=5)
        cpy.connect()
        cpy.downloadNewFiles()
        cpy.close()

        self.assertEqual(4, cpy.connect_count)
        self.assertEqual([99, 300, 600], schedule.seek_offsets)
        self.assertEqual(self.CONTENTS, open(self.downloaded_path(), "rb").read())
        self.assertFalse(os.path.exists(self.remote_file))

    def test_retry_limit_exceeded_raises_and_keeps_remote_file(self):
        schedule = DropSchedule(drop_after_bytes=[100, 200, 300, 400])
        cpy = self.make_copy(schedule, reconnect_attempts=2)
        cpy.connect()
        cpy.downloadNewFiles()  # IOError is caught & logged internally
        cpy.close()

        # initial connect + 2 allowed reconnects, 3rd drop is fatal
        self.assertEqual(3, cpy.connect_count)
        self.assertFalse(os.path.exists(self.downloaded_path()))
        self.assertTrue(os.path.exists(self.tmp_path()))
        self.assertTrue(os.path.exists(self.remote_file))

    def test_remote_file_change_refuses_resume(self):
        def grow_remote_file():
            with open(self.remote_file, "ab") as f:
                f.write(b"extra-bytes-appended-after-drop")

        schedule = DropSchedule(drop_after_bytes=[216], on_drop=grow_remote_file)
        cpy = self.make_copy(schedule)
        cpy.connect()
        cpy.downloadNewFiles()  # IOError is caught & logged internally
        cpy.close()

        self.assertFalse(os.path.exists(self.downloaded_path()))
        self.assertTrue(os.path.exists(self.tmp_path()))
        # the remote file must not be removed, we never finished the
        # download
        self.assertTrue(os.path.exists(self.remote_file))

    def test_non_retryable_sftp_error_is_not_retried(self):
        schedule = DropSchedule(
            drop_after_bytes=[100],
            exception_factory=lambda: PermissionError("Permission denied"),
        )
        cpy = self.make_copy(schedule)
        cpy.connect()
        cpy.downloadNewFiles()  # IOError is caught & logged internally
        cpy.close()

        # no reconnect must have been attempted for a non-connection error
        self.assertEqual(1, cpy.connect_count)
        self.assertFalse(os.path.exists(self.downloaded_path()))
        self.assertTrue(os.path.exists(self.remote_file))

    def test_reconnect_itself_fails_once_then_succeeds(self):
        schedule = DropSchedule(drop_after_bytes=[216], reconnect_failures=1)
        cpy = self.make_copy(schedule, reconnect_attempts=3)
        cpy.connect()
        cpy.downloadNewFiles()
        cpy.close()

        # initial connect + 1 failed reconnect attempt (not counted as a
        # successful connection) + 1 successful reconnect
        self.assertEqual(2, cpy.connect_count)
        self.assertEqual(3, cpy.connect_attempts)
        self.assertEqual([216], schedule.seek_offsets)
        self.assertEqual(self.CONTENTS, open(self.downloaded_path(), "rb").read())
        self.assertFalse(os.path.exists(self.remote_file))

    def test_all_reconnects_fail_raises_and_keeps_remote_file(self):
        schedule = DropSchedule(drop_after_bytes=[216], reconnect_failures=99)
        cpy = self.make_copy(schedule, reconnect_attempts=3)
        cpy.connect()
        cpy.downloadNewFiles()  # IOError/SSHException is caught & logged
        cpy.close()

        # only the initial connect ever succeeded, all reconnects failed
        self.assertEqual(1, cpy.connect_count)
        self.assertEqual(4, cpy.connect_attempts)  # initial + 3 failed
        self.assertFalse(os.path.exists(self.downloaded_path()))
        self.assertTrue(os.path.exists(self.tmp_path()))
        self.assertTrue(os.path.exists(self.remote_file))

    def test_premature_eof_is_not_accepted_as_successful_download(self):
        schedule = DropSchedule(premature_eof_after_bytes=40)
        cpy = self.make_copy(schedule)
        cpy.connect()
        cpy.downloadNewFiles()
        cpy.close()

        # initial connect + one reconnect triggered by the premature EOF
        self.assertEqual(2, cpy.connect_count)
        self.assertEqual(self.CONTENTS, open(self.downloaded_path(), "rb").read())
        self.assertFalse(os.path.exists(self.remote_file))

    def test_premature_eof_with_exhausted_reconnects_keeps_remote_file(self):
        schedule = DropSchedule(premature_eof_after_bytes=40, reconnect_failures=99)
        cpy = self.make_copy(schedule, reconnect_attempts=2)
        cpy.connect()
        cpy.downloadNewFiles()  # IOError is caught & logged internally
        cpy.close()

        self.assertFalse(os.path.exists(self.downloaded_path()))
        self.assertTrue(os.path.exists(self.tmp_path()))
        self.assertTrue(os.path.exists(self.remote_file))
