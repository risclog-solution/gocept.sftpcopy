# Copyright (c) 2012-2014 gocept gmbh & co. kg
# See also LICENSE.txt

import gocept.sftpcopy.sftpcopy
import gocept.sftpcopy.testing
import os
import os.path
import shutil
import tempfile
import unittest


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
