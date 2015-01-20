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

import sys
import unittest

from mock import patch
from mock import MagicMock

from . import cli
from . import errors
from . import get_deployment_driver


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

    def test_main_interrupt(self):
        with patch('virtdeploy.cli.parse_command_line') as func_mock:
            func_mock.side_effect = KeyboardInterrupt
            with self.assertRaises(SystemExit) as cm:
                cli.main()
            assert cm.exception.code == 130

    @patch('sys.stdout')
    def test_get_deployment_driver(self, stdout_mock):
        driver_mock = MagicMock()
        with patch.dict('sys.modules',
                        {'virtdeploy.drivers.libvirt': driver_mock}):
            driver = get_deployment_driver('libvirt')
        assert driver is driver_mock

    @patch('sys.stdout')
    def test_instance_create(self, stdout_mock):
        with patch('virtdeploy.get_deployment_driver') as driver_mock:
            instance_create = driver_mock.return_value.instance_create
            instance_create.return_value = {
                'name': 'test01',
                'password': 'password',
                'mac': '52:54:00:a0:b0:01',
                'hostname': 'vm-test01.example.com',
                'ipaddress': '192.168.122.2',
            }
            cli.parse_command_line(['create', 'test01', 'base01'])
        driver_mock.assert_called_with('libvirt')
        instance_create.assert_called_with('test01', 'base01')

    @patch('sys.stderr')
    def test_instance_create_fail1(self, stderr_mock):
        with patch('virtdeploy.get_deployment_driver'):
            with self.assertRaises(SystemExit) as cm:
                cli.parse_command_line(['create', 'test01'])
            assert cm.exception.code == 2

    @patch('sys.stderr')
    def test_instance_create_fail2(self, stderr_mock):
        with patch('virtdeploy.get_deployment_driver'):
            with self.assertRaises(SystemExit) as cm:
                cli.parse_command_line(['create'])
            assert cm.exception.code == 2

    def test_instance_delete(self):
        with patch('virtdeploy.get_deployment_driver') as driver_mock:
            instance_delete = driver_mock.return_value.instance_delete
            cli.parse_command_line(['delete', 'test01'])
        driver_mock.assert_called_with('libvirt')
        instance_delete.assert_called_with('test01')

    def test_instance_address(self):
        with patch('virtdeploy.get_deployment_driver') as driver_mock:
            instance_address = driver_mock.return_value.instance_address
            cli.parse_command_line(['address', 'test01'])
        driver_mock.assert_called_with('libvirt')
        instance_address.assert_called_with('test01')

    def test_instance_start(self):
        with patch('virtdeploy.get_deployment_driver') as driver_mock:
            instance_start = driver_mock.return_value.instance_start
            cli.parse_command_line(['start', 'test01'])
        driver_mock.assert_called_with('libvirt')
        instance_start.assert_called_with('test01')

    def test_instance_stop(self):
        with patch('virtdeploy.get_deployment_driver') as driver_mock:
            instance_stop = driver_mock.return_value.instance_stop
            cli.parse_command_line(['stop', 'test01'])
        driver_mock.assert_called_with('libvirt')
        instance_stop.assert_called_with('test01')

    @patch('sys.stdout')
    def test_template_list(self, stdout_mock):
        with patch('virtdeploy.get_deployment_driver') as driver_mock:
            template_list = driver_mock.return_value.template_list
            template_list.return_value = [
                {'id': 'centos-6', 'name': 'CentOS 6'},
                {'id': 'centos-7', 'name': 'CentOS 7'},
            ]
            cli.parse_command_line(['templates'])
        driver_mock.assert_called_with('libvirt')
        template_list.assert_called_with()
