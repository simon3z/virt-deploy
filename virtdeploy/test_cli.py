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
from . import errors


if sys.version_info[0] == 3:  # pragma: no cover
    from io import StringIO
else:  # pragma: no cover
    from StringIO import StringIO


class TestCommandLine(unittest.TestCase):
    HELP_OUTPUT = """\
usage: python -m unittest [-h] [-v]
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
  -v, --version         show program's version number and exit
"""

    def test_help(self):
        with patch('sys.stdout', new=StringIO()) as stdout_mock:
            with self.assertRaises(SystemExit) as cm:
                cli.parse_command_line(['--help'])
            assert cm.exception.code == 0
        assert stdout_mock.getvalue() == self.HELP_OUTPUT

    def test_main_success(self):
        with patch('virtdeploy.cli.parse_command_line') as func_mock:
            cli.main()
            func_mock.assert_call()

    @patch('sys.stderr')
    def test_main_failure(self, stderr_mock):
        with patch('virtdeploy.cli.parse_command_line') as func_mock:
            func_mock.side_effect = errors.VirtDeployException
            with self.assertRaises(SystemExit) as cm:
                cli.main()
            assert cm.exception.code == 1
