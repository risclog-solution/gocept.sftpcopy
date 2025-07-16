from io import StringIO
import paramiko
import sftpserver.stub_sftp
import socket
import threading
import time


class SFTPServer(sftpserver.stub_sftp.StubServer):
    username = "user"
    password = "secret"

    def get_allowed_auths(self, username):
        return "password"

    def check_auth_password(self, username, password):
        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED  # pragma: nocover


class Transport(paramiko.Transport):
    def _unlink_channel(self, chanid):
        # Because they keep a reference to their Transport, Channels aren't
        # garbage-collected properly, making zope.testrunner complain.
        # This issue is filed upstream at
        # <https://github.com/paramiko/paramiko/issues/64>
        chan = self._channels.get(chanid)
        super(Transport, self)._unlink_channel(chanid)
        chan.transport = None


class SFTPThread(threading.Thread):
    def __init__(self, directory, host="localhost"):
        self.host = host
        self.directory = directory
        super(SFTPThread, self).__init__()
        self.daemon = True
        self.running = False

    def start(self):
        super(SFTPThread, self).start()
        self.wait_until_running()

    def run(self):
        # I'd rather use fs.expose.sftp, since it has a much cleaner API, but
        # since it doesn't work at all in lots of obscure ways, I've hacked
        # this together from sftpserver

        sftpserver.stub_sftp.StubSFTPServer.ROOT = self.directory

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        server_socket.settimeout(0.1)
        server_socket.bind((self.host, 0))  # choose port automatically
        server_socket.listen(10)
        self.port = server_socket.getsockname()[1]

        self.running = True

        while self.running:
            try:
                conn, addr = server_socket.accept()
            except socket.timeout:
                continue

            transport = Transport(conn)
            transport.add_server_key(DEFAULT_HOST_KEY)
            transport.set_subsystem_handler(
                "sftp", paramiko.SFTPServer, sftpserver.stub_sftp.StubSFTPServer
            )

            transport.start_server(server=SFTPServer())
            while transport.is_active():
                time.sleep(0.01)

    def wait_until_running(self, timeout=100):
        for i in range(timeout):
            if self.running:
                break
            time.sleep(0.05)
        else:  # pragma: nocover
            raise RuntimeError("SFTP server did not start up.")

    def stop(self):
        self.running = False
        self.join()


DEFAULT_HOST_KEY = paramiko.RSAKey.from_private_key(
    StringIO(
        "-----BEGIN RSA PRIVATE KEY-----\nMIICXgIBAAKCAIEAl7sAF0x2O/Hw"
        "LhG68b1uG8KHSOTqe3Cdlj5i/1RhO7E2BJ4B\n3jhKYDYtupRnMFbpu7fb21A"
        "24w3Y3W5gXzywBxR6dP2HgiSDVecoDg2uSYPjnlDk\nHrRuviSBG3XpJ/awn1"
        "DObxRIvJP4/sCqcMY8Ro/3qfmid5WmMpdCZ3EBeC0CAwEA\nAQKCAIBSGefUs"
        "5UOnr190C49/GiGMN6PPP78SFWdJKjgzEHI0P0PxofwPLlSEj7w\nRLkJWR4k"
        "azpWE7N/bNC6EK2pGueMN9Ag2GxdIRC5r1y8pdYbAkuFFwq9Tqa6j5B0\nGkk"
        "wEhrcFNBGx8UfzHESXe/uE16F+e8l6xBMcXLMJVo9Xjui6QJBAL9MsJEx93iO"
        "\nzwjoRpSNzWyZFhiHbcGJ0NahWzc3wASRU6L9M3JZ1VkabRuWwKNuEzEHNK8"
        "cLbRl\nTyH0mceWXcsCQQDLDEuWcOeoDteEpNhVJFkXJJfwZ4Rlxu42MDsQQ/"
        "paJCjt2ONU\nWBn/P6iYDTvxrt/8+CtLfYc+QQkrTnKn3cLnAkEAk3ixXR0h4"
        "6Rj4j/9uSOfyyow\nqHQunlZ50hvNz8GAm4TU7v82m96449nFZtFObC69SLx/"
        "VsboTPsUh96idgRrBQJA\nQBfGeFt1VGAy+YTLYLzTfnGnoFQcv7+2i9ZXnn/"
        "Gs9N8M+/lekdBFYgzoKN0y4pG\n2+Q+Tlr2aNlAmrHtkT13+wJAJVgZATPI5X"
        "3UO0Wdf24f/w9+OY+QxKGl86tTQXzE\n4bwvYtUGufMIHiNeWP66i6fYCucXC"
        "MYtx6Xgu2hpdZZpFw==\n-----END RSA PRIVATE KEY-----\n"
    )
)
