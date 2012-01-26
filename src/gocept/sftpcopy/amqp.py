# Copyright (c) 2012 gocept gmbh & co. kg
# See also LICENSE.txt

import gocept.amqprun.handler
import gocept.amqprun.interfaces
import time
import zope.component.zcml
import zope.interface


class Uploader(object):

    def __init__(self, hostname, port, username, password, remote_path):
        self.sftp = gocept.sftpcopy.SFTPCopy(
            '/dev/null', hostname, port, username, password, remote_path)

    def __call__(self, message):
        self.sftp.connect()
        self.sftp.uploadFileContents(
            self.generate_filename(message), message.body)
        self.sftp.close()

    def generate_filename(self, message):
        # XXX extract from gocept.amqprun.writefiles
        return '%s-%s' % (message.routing_key, time.time())


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
