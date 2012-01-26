# Copyright (c) 2012 gocept gmbh & co. kg
# See also LICENSE.txt

import gocept.amqprun.handler
import gocept.amqprun.interfaces
import zope.component.zcml
import zope.interface


class Uploader(object):

    def __init__(self, hostname, port, username, password, remote_path):
        self.sftp = gocept.sftpcopy.SFTPCopy(
            '/dev/null', hostname, port, username, password, remote_path)

    def __call__(self, message):
        self.sftp.connect()
        self.sftp.uploadFileContents(
            self.determine_filename(message), message.body)
        self.sftp.close()

    def determine_filename(self, message):
        filename = message.header.headers and message.header.headers.get(
            'X-Filename')
        if not filename:
            filename = message.generate_filename('${routing_key}-${unique}')
        return filename


class ISFTPDirective(zope.interface.Interface):

    routing_key = zope.configuration.fields.Tokens(
        title=u"Routing key(s) to listen on",
        value_type=zope.schema.TextLine())

    queue_name = zope.schema.TextLine(title=u"Queue name")

    arguments = gocept.amqprun.interfaces.RepresentableDict(
        key_type=zope.schema.TextLine(),
        value_type=zope.schema.TextLine(),
        required=False)

    hostname = zope.schema.TextLine(title=u"Remote hostname")
    port = zope.schema.Int(title=u"Remote port")
    username = zope.schema.TextLine(title=u"Username")
    password = zope.schema.TextLine(title=u"Password")
    remote_path = zope.schema.TextLine(title=u"Path on remote machine")


def sftp_directive(
        _context, routing_key, queue_name,
        hostname, port, username, password, remote_path, arguments=None):
    uploader = Uploader(hostname, port, username, password, remote_path)
    handler = gocept.amqprun.handler.HandlerDeclaration(
        queue_name, routing_key, uploader, arguments)
    zope.component.zcml.utility(
        _context,
        component=handler,
        name=unicode('gocept.sftpcopy.amqp.%s' % queue_name))
