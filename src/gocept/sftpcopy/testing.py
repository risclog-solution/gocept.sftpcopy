# Copyright (c) 2012 gocept gmbh & co. kg
# See also LICENSE.txt

from StringIO import StringIO
import paramiko
import sftpserver.stub_sftp
import socket
import threading
import time


class SFTPServer(sftpserver.stub_sftp.StubServer):

    username = 'user'
    password = 'secret'

    def get_allowed_auths(self, username):
        return 'password'

    def check_auth_password(self, username, password):
        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED


class SFTPThread(threading.Thread):

    def __init__(self, host, port, directory):
        self.host = host
        self.port = port
        self.directory = directory
        super(SFTPThread, self).__init__()
        self.daemon = True

    def run(self):
        self.running = True

        # I'd rather use fs.expose.sftp, since it has a much cleaner API, but
        # since it doesn't work at all in lots of obscure ways, I've hacked
        # this together from sftpserver

        sftpserver.stub_sftp.StubSFTPServer.ROOT = self.directory

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        server_socket.settimeout(0.1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(10)

        while self.running:
            try:
                conn, addr = server_socket.accept()
            except socket.timeout:
                continue

            transport = paramiko.Transport(conn)
            transport.add_server_key(DEFAULT_HOST_KEY)
            transport.set_subsystem_handler(
                'sftp', paramiko.SFTPServer,
                sftpserver.stub_sftp.StubSFTPServer)

            transport.start_server(server=SFTPServer())
            while transport.is_active():
                time.sleep(0.01)

    def stop(self):
        self.running = False
        self.join()


DEFAULT_HOST_KEY = paramiko.RSAKey.from_private_key(StringIO("-----BEGIN RSA PRIVATE KEY-----\nMIICXgIBAAKCAIEAl7sAF0x2O/HwLhG68b1uG8KHSOTqe3Cdlj5i/1RhO7E2BJ4B\n3jhKYDYtupRnMFbpu7fb21A24w3Y3W5gXzywBxR6dP2HgiSDVecoDg2uSYPjnlDk\nHrRuviSBG3XpJ/awn1DObxRIvJP4/sCqcMY8Ro/3qfmid5WmMpdCZ3EBeC0CAwEA\nAQKCAIBSGefUs5UOnr190C49/GiGMN6PPP78SFWdJKjgzEHI0P0PxofwPLlSEj7w\nRLkJWR4kazpWE7N/bNC6EK2pGueMN9Ag2GxdIRC5r1y8pdYbAkuFFwq9Tqa6j5B0\nGkkwEhrcFNBGx8UfzHESXe/uE16F+e8l6xBMcXLMJVo9Xjui6QJBAL9MsJEx93iO\nzwjoRpSNzWyZFhiHbcGJ0NahWzc3wASRU6L9M3JZ1VkabRuWwKNuEzEHNK8cLbRl\nTyH0mceWXcsCQQDLDEuWcOeoDteEpNhVJFkXJJfwZ4Rlxu42MDsQQ/paJCjt2ONU\nWBn/P6iYDTvxrt/8+CtLfYc+QQkrTnKn3cLnAkEAk3ixXR0h46Rj4j/9uSOfyyow\nqHQunlZ50hvNz8GAm4TU7v82m96449nFZtFObC69SLx/VsboTPsUh96idgRrBQJA\nQBfGeFt1VGAy+YTLYLzTfnGnoFQcv7+2i9ZXnn/Gs9N8M+/lekdBFYgzoKN0y4pG\n2+Q+Tlr2aNlAmrHtkT13+wJAJVgZATPI5X3UO0Wdf24f/w9+OY+QxKGl86tTQXzE\n4bwvYtUGufMIHiNeWP66i6fYCucXCMYtx6Xgu2hpdZZpFw==\n-----END RSA PRIVATE KEY-----\n"))
