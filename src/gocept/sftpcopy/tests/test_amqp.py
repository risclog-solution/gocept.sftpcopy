# Copyright (c) 2012 gocept gmbh & co. kg
# See also LICENSE.txt

import gocept.amqprun.testing
import os
import os.path
import shutil
import tempfile
import time


class IntegrationTest(gocept.amqprun.testing.MainTestCase):

    def setUp(self):
        super(IntegrationTest, self).setUp()
        self.tmpdir = tempfile.mkdtemp()
        self.sftp = gocept.sftpcopy.testing.SFTPThread(
            'localhost', 8022, self.tmpdir)
        self.sftp.start()

    def tearDown(self):
        self.sftp.stop()
        shutil.rmtree(self.tmpdir)
        super(IntegrationTest, self).tearDown()

    def test_message_contents_should_be_uploaded(self):
        self.make_config(
            __name__, 'upload', dict(
                routing_key='test.data',
                queue_name=self.get_queue_name('test'),
                hostname='localhost', port='8022',
                username='user', password='secret',
                remote_path='/'
                ))
        self.start_server()
        body = 'This is only a test.'
        self.send_message(body, routing_key='test.data')
        self.wait_for_processing()
        time.sleep(1)

        files = os.listdir(self.tmpdir)
        self.assertEqual(1, len(files))
        uploaded = os.path.join(self.tmpdir, files[0])
        self.assertTrue(os.path.isfile(uploaded))
        self.assertEqual('This is only a test.', open(uploaded).read())
