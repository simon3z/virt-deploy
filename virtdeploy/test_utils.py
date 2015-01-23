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

import unittest

from mock import patch
from subprocess import CalledProcessError

from . import utils


class TestRandomPassword(unittest.TestCase):
    def test_random_password(self):
        for size in range(6, 24):
            self.assertEqual(len(utils.random_password(size=size)), size)


class TestExecute(unittest.TestCase):
    def test_execute_success(self):
        command = ('command', 'arg1', 'arg2')
        optargs = {'stdout': 1, 'stderr': 2, 'cwd': '/path'}
        outputs = ('hello stdout', 'hello stderr')

        with patch('subprocess.Popen') as popen_mock:
            popen_mock.return_value.communicate.return_value = outputs
            popen_mock.return_value.returncode = 0

            self.assertEqual(utils.execute(command, **optargs), outputs)

        popen_mock.assert_called_once_with(command, **optargs)

    def test_execute_failure(self):
        command = ('command', 'arg1', 'arg2')
        optargs = {'stdout': 1, 'stderr': 2, 'cwd': '/path'}
        outputs = ('', 'command error output')

        with patch('subprocess.Popen') as popen_mock:
            popen_mock.return_value.communicate.return_value = outputs
            popen_mock.return_value.returncode = 1

            with self.assertRaises(CalledProcessError) as cm:
                utils.execute(command, **optargs)

            self.assertEqual(cm.exception.returncode, 1)
