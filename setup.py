# Copyright (c) 2007-2020 gocept gmbh & co. kg
# See also LICENSE.txt

from setuptools import setup, find_packages
import os.path


setup(
    name="gocept.sftpcopy",
    version="2.1",
    author="Christian Zagrodnick",
    author_email="mail@gocept.com",
    description="Upload/download files via SFTP to a maildir structure",
    long_description=(
        open(os.path.join(os.path.dirname(__file__), "README.rst")).read()
        + "\n\n"
        + open(os.path.join(os.path.dirname(__file__), "CHANGES.rst")).read()
        + "\n\n"
    ),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved",
        "Natural Language :: English",
        "License :: OSI Approved :: Zope Public License",
        "Programming Language :: Python",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Operating System :: POSIX :: BSD",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Communications",
        "Topic :: Internet",
        "Topic :: Internet :: File Transfer Protocol (FTP)",
    ],
    license="ZPL 2.1",
    url="https://github.com/gocept/gocept.sftpcopy",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    namespace_packages=["gocept"],
    install_requires=[
        'configparser;python_version<"3"',
        "setuptools",
        "gocept.filestore",
        "paramiko",
    ],
    extras_require=dict(
        test=[
            "sftpserver",
        ],
    ),
    entry_points=dict(console_scripts=["sftpcopy=gocept.sftpcopy.sftpcopy:main"]),
)
