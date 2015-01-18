#
# Copyright 2015 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

from __future__ import absolute_import

from mock import patch
import sys
import unittest

from . import cli


if sys.version_info >= (3, 0):
    from io import StringIO
else:
    from StringIO import StringIO


class TestCommandLine(unittest.TestCase):
    HELP_OUTPUT = """\
usage: python -m unittest [-h]
                          {create,start,stop,delete,templates,address} ...

positional arguments:
  {create,start,stop,delete,templates,address}
    create              create a new instance
    start               start an instance
    stop                stop an instance
    delete              delete an instance
    templates           list all the templates
    address             instance ip address

optional arguments:
  -h, --help            show this help message and exit
"""

    def test_help(self):
        output = StringIO()

        def wrap_print_help(spec):
            return lambda x: spec(x, file=output)

        with patch('argparse.ArgumentParser.print_help',
                   spec=True, new_callable=wrap_print_help):
            try:
                cli.parse_command_line(['--help'])
            except SystemExit as e:
                if e.code != 0:
                    raise
            else:
                raise AssertionError('SystemExit was expected')

        assert output.getvalue() == self.HELP_OUTPUT
