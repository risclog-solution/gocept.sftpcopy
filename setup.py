# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import os.path

from setuptools import setup, find_packages


setup(
    name = 'gocept.sftpcopy',
    version = "0.1",
    author = "Christian Zagrodnick",
    author_email = "cz@gocept.com",
    description = "Copying files save to another machine",
    long_description = file(os.path.join(os.path.dirname(__file__),
                                         'README.txt')).read(),
    license = "ZPL 2.1",
    url='http://pypi.python.org/pypi/gocept.sftpcopy',

    packages = find_packages('src'),
    package_dir = {'': 'src'},

    include_package_data = True,
    zip_safe = False,

    namespace_packages = ['gocept'],
    install_requires = [
        'setuptools',
        'gocept.filestore',
        'paramiko',
    ],
    extras_require = dict(
        test=[]),
    entry_points = dict(
        console_scripts =
            ['sftpcopy = gocept.sftpcopy.sftpcopy:main']),
)
