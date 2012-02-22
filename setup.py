# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt

from setuptools import setup, find_packages
import os.path


setup(
    name='gocept.sftpcopy',
    version='0.2',
    author="Christian Zagrodnick <cz at gocept dot com>",
    author_email="cz@gocept.com",
    description="Upload/download files via SFTP to a  maildir structure",
    long_description=(
        open(os.path.join(os.path.dirname(__file__), 'README.txt')).read()
        + '\n\n'
        + open(os.path.join(os.path.dirname(__file__), 'CHANGES.txt')).read()
        + '\n\n'
        ),
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Zope Public License',
        'Programming Language :: Python',
        'Operating System :: Unix',
    ],

    license="ZPL 2.1",
    url='https://code.gocept.com/hg/public/gocept.sftpcopy',

    packages=find_packages('src'),
    package_dir={'': 'src'},

    include_package_data=True,
    zip_safe=False,

    namespace_packages=['gocept'],
    install_requires=[
        'setuptools',
        'gocept.filestore',
        'paramiko',
    ],
    extras_require=dict(
        amqp=[
            'zope.component[zcml]',
            'zope.configuration',
            'zope.interface',
            'gocept.amqprun>=0.6dev',
        ],
        test=[
            'sftpserver',
        ]),
    entry_points=dict(console_scripts=[
            'sftpcopy=gocept.sftpcopy.sftpcopy:main']),
)
