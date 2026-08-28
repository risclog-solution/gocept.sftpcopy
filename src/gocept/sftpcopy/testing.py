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
        """-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAioZRmDzRqXTTYuyYsaPSivadCM2P7+fqcUd0syzem9ittfPu
3oQU55dBv4XrtIS6cjYJi/UQ6GmrTJgwNT2ovA9yYmOH0TC0e7fos0A+4ruV7/qJ
xoashCCKHm8qThLVGOzSAKocQ/1vwDqMbdNRZXZcTHo44G6hwQl2FXr7R9liwZwA
ExjvasyCqe8s207qpeaShsIRxM6h+FLKoJd0ZZYygq9vY2bJS3KhBGkOf0ctpq11
/LEPOQdQW6/d6MXvvbHcA/w668M1FErFv5hZiwSnbn9tzURoX4Q8ACcMEs0/WZ2o
HkQaO464/faKyBXRj42znSqo+xQHruB4Xen5PQIDAQABAoIBAB9uNplKQ3All8j8
UfEMcLsjFaJnsd8HSgSF6A63gZLu6Qs929cVNQEPKtXf9wkwjHVZmXTuF/YD8+Af
L+EEqoJxJsz4NFrcqDbiFaSGUT50vaKDwDsRV5drIquhIYIxd7R+F3AbKOqsWGzP
XAmXRwK0hmC74qfZsk3wbaCWFOnKLcz6Hlrpaac6qBcmQDZE0uBwaw4U73qYSxm9
UPM/jyPVqcoFpHjVbWx8k2viuEd0oI3nnLDHG15MrdGcT1QduqtUX+KVW8LhbSII
NwRRrp0R4oz2Yjqioqesitcgxi0oUcQnZ9CAuYsWAIn4aUpTe/0Yx0SnJuYT+NM7
CGk4AKkCgYEAvxlazQ6Fcbz3z46zXpHg+X7KEINSWqqNajxK4YCKgX83KEAHekTK
9YTDezxhxnLOvaDfJdwZxB8qy4tueyrL5yfTbWXeMhIFKuthwKw/8rztORgXgi0e
o9slMpZGHOnKjYVSS77FazTVqftbxi1VQZVczEMNAN4W9FQP4XaxiT8CgYEAuZID
XxKg1zmVfqLARpUXtIf64HN6OXgennpuZu3XIBWzeSLRBqvrFa4Qw14UXNerxm/r
8s+B+kP4ea/jKg9jubfwNl/GQxrd44lmMhGTx8B7fwW3XkzXnqvYBWQIKfiFqDb0
oLi7jueauxDpbD1tyHhEUSLYfbTi7SY0nq4xwoMCgYB41a90uhnnMXYA6FrDEbsQ
B/v9NQx+CBojcrxmmsD54VcfPF1+EsHDPY/d/PBWa4IOpgp0BhjEynBlBGV3vDfy
klw+cItvXbWmze+hxUkqVAwsbe9vgNg/A/MhaaQr5CkQE51WB+sNPvtb4HTHeyLN
tYRYJI20XrplBEKGbmcUQQKBgF/2rT2mIX0Lb06slWgqw7Z9N3SI4yUDBDqKL7uU
tVIHRueW5KdhklGE0XBmn3sfoNoemNLZEms8aStslLn0eWraPyOvRZUAOMzpCetM
gbKjzHl0mE3wyPRqA21OPJaPyXai7MCMp5mQFck1RrDN1476+sFGltPzDgL7ZezF
QkBHAoGAL9T+CSgP3E09BG33BTiKulRNUIRvXRr28R7Sidk8zOrwnG6ttmK0lKzO
kDb6HJJoWJ3c9HeL9ejZ31N+LLP7STdAmD4eiHbdoHCA2BO3BHCV3ukazAMAWTGR
Csbjho/p9grnvCISYJROjb8HQshQEOIYxKlpyiUNDaRT9vD6ItI=
-----END RSA PRIVATE KEY-----
"""
    )
)
