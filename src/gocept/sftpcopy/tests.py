# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import doctest


def test_suite():
    return doctest.DocFileSuite('README.txt')
