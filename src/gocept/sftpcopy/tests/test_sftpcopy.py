# Copyright (c) 2012 gocept gmbh & co. kg
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
        server_dir = os.path.join(self.tmpdir, 'server')
        os.mkdir(server_dir)
        self.sftp = gocept.sftpcopy.testing.SFTPThread(
            'localhost', 8022, server_dir)
        self.sftp.start()

        self.config = dict(local_path=self.tmpdir, remote_path='/',
                           hostname='localhost', port=8022,
                           username='user', password='secret')

    def tearDown(self):
        self.sftp.stop()
        shutil.rmtree(self.tmpdir)

    def test_upload(self):
        os.mkdir(os.path.join(self.tmpdir, 'new'))
        f = open(os.path.join(self.tmpdir, 'new', 'foo'), 'w')
        f.write('contents')
        f.close()

        self.config['mode'] = 'upload'
        gocept.sftpcopy.sftpcopy.main(self.config)

        uploaded = os.path.join(self.tmpdir, 'server', 'foo')
        self.assertTrue(os.path.isfile(uploaded))
        self.assertEqual('contents', open(uploaded).read())

        self.assertEqual(0, len(os.listdir(os.path.join(self.tmpdir, 'new'))))
        self.assertEqual(1, len(os.listdir(os.path.join(self.tmpdir, 'cur'))))

    def test_download(self):
        f = open(os.path.join(self.tmpdir, 'server', 'foo'), 'w')
        f.write('contents')
        f.close()

        self.config['mode'] = 'download'
        gocept.sftpcopy.sftpcopy.main(self.config)

        downloaded = os.path.join(self.tmpdir, 'new', 'foo')
        self.assertTrue(os.path.isfile(downloaded))
        self.assertEqual('contents', open(downloaded).read())

        self.assertEqual(
            0, len(os.listdir(os.path.join(self.tmpdir, 'server'))))
