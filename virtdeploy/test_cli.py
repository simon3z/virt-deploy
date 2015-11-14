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

from . import cli
from . import errors


if sys.version_info[0] == 3:  # pragma: no cover
    from io import StringIO
else:  # pragma: no cover
    from StringIO import StringIO


class TestCommandLine(unittest.TestCase):
    HELP_OUTPUT = """\
usage: python -m unittest [-h] [-v]
                          {create,start,stop,delete,templates,address,ssh} ...

positional arguments:
  {create,start,stop,delete,templates,address,ssh}
    create              create a new instance
    start               start an instance
    stop                stop an instance
    delete              delete an instance
    templates           list all the templates
    address             instance ip address
    ssh                 connects to the instance

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
"""

    def test_help(self):
        with patch('sys.stdout', new=StringIO()) as stdout_mock:
            with self.assertRaises(SystemExit) as cm:
                cli.parse_command_line(['--help'])

        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(stdout_mock.getvalue(), self.HELP_OUTPUT)

    def test_main_success(self):
        with patch.object(sys, 'argv', []):
            with patch('virtdeploy.cli.parse_command_line') as func_mock:
                cli.main()
                func_mock.assert_called_once_with([])

    @patch('sys.stderr')
    def test_main_failure(self, stderr_mock):
        with patch('virtdeploy.cli.parse_command_line') as func_mock:
            func_mock.side_effect = errors.VirtDeployException

            with self.assertRaises(SystemExit) as cm:
                cli.main()

        self.assertEqual(cm.exception.code, 1)

    def test_main_interrupt(self):
        with patch('virtdeploy.cli.parse_command_line') as func_mock:
            func_mock.side_effect = KeyboardInterrupt

            with self.assertRaises(SystemExit) as cm:
                cli.main()

        self.assertEqual(cm.exception.code, cli.EXITCODE_KEYBINT)

    @patch('sys.stdout')
    @patch('virtdeploy.get_driver')
    def test_instance_create(self, driver_mock, stdout_mock):
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
    @patch('virtdeploy.get_driver')
    def test_instance_create_fail1(self, driver_mock, stderr_mock):
        with self.assertRaises(SystemExit) as cm:
            cli.parse_command_line(['create', 'test01'])

        self.assertEqual(cm.exception.code, 2)

    @patch('sys.stderr')
    @patch('virtdeploy.get_driver')
    def test_instance_create_fail2(self, driver_mock, stderr_mock):
        with self.assertRaises(SystemExit) as cm:
            cli.parse_command_line(['create'])

        self.assertEqual(cm.exception.code, 2)

    @patch('virtdeploy.get_driver')
    def test_instance_delete(self, driver_mock):
        instance_delete = driver_mock.return_value.instance_delete

        cli.parse_command_line(['delete', 'test01'])

        driver_mock.assert_called_with('libvirt')
        instance_delete.assert_called_with('test01')

    @patch('sys.stdout')
    @patch('virtdeploy.get_driver')
    def test_instance_address(self, driver_mock, stdout_mock):
        instance_address = driver_mock.return_value.instance_address

        cli.parse_command_line(['address', 'test01'])

        driver_mock.assert_called_with('libvirt')
        instance_address.assert_called_with('test01')

    @patch('virtdeploy.get_driver')
    def test_instance_start(self, driver_mock):
        instance_start = driver_mock.return_value.instance_start

        cli.parse_command_line(['start', 'test01'])

        driver_mock.assert_called_with('libvirt')
        instance_start.assert_called_with('test01')

    @patch('virtdeploy.get_driver')
    @patch('virtdeploy.utils.wait_tcp_access')
    def test_instance_start_wait_success(self, wait_mock, driver_mock):
        instance_start = driver_mock.return_value.instance_start
        wait_mock.return_value = '192.168.122.2'

        cli.parse_command_line(['start', '--wait', 'test01'])

        driver_mock.assert_called_with('libvirt')
        instance_start.assert_called_with('test01')
        wait_mock.assert_called_with(driver_mock.return_value, 'test01')

    @patch('virtdeploy.get_driver')
    @patch('virtdeploy.utils.wait_tcp_access')
    def test_instance_start_wait_fail(self, wait_mock, driver_mock):
        instance_start = driver_mock.return_value.instance_start
        wait_mock.return_value = None

        cli.parse_command_line(['start', '--wait', 'test01'])

        driver_mock.assert_called_with('libvirt')
        instance_start.assert_called_with('test01')
        wait_mock.assert_called_with(driver_mock.return_value, 'test01')

    @patch('virtdeploy.get_driver')
    def test_instance_stop(self, driver_mock):
        instance_stop = driver_mock.return_value.instance_stop

        cli.parse_command_line(['stop', 'test01'])

        driver_mock.assert_called_with('libvirt')
        instance_stop.assert_called_with('test01')

    @patch('sys.stdout')
    @patch('virtdeploy.get_driver')
    def test_template_list(self, driver_mock, stdout_mock):
        template_list = driver_mock.return_value.template_list
        template_list.return_value = [
            {'id': 'centos-6', 'name': 'CentOS 6'},
            {'id': 'centos-7', 'name': 'CentOS 7'},
        ]

        cli.parse_command_line(['templates'])

        driver_mock.assert_called_with('libvirt')
        template_list.assert_called_with()

    @patch('virtdeploy.get_driver')
    def test_instance_ssh(self, driver_mock):
        instance_address = driver_mock.return_value.instance_address
        instance_address.return_value = ['192.168.122.2']

        with patch('subprocess.call') as call_mock:
            cli.parse_command_line(['ssh', 'test01'])

        call_mock.assert_called_with(['ssh', '-A',
                                      '-o', 'StrictHostKeychecking=no',
                                      '-o', 'UserKnownHostsFile=/dev/null',
                                      '-o', 'LogLevel=QUIET',
                                      '192.168.122.2'])

    @patch('virtdeploy.get_driver')
    def test_instance_ssh_user(self, driver_mock):
        instance_address = driver_mock.return_value.instance_address
        instance_address.return_value = ['192.168.122.3']

        with patch('subprocess.call') as call_mock:
            cli.parse_command_line(['ssh', 'root@test02'])

        call_mock.assert_called_with(['ssh', '-A',
                                      '-o', 'StrictHostKeychecking=no',
                                      '-o', 'UserKnownHostsFile=/dev/null',
                                      '-o', 'LogLevel=QUIET',
                                      '-l', 'root',
                                      '192.168.122.3'])
