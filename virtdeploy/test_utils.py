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
from mock import Mock
from mock import patch

from . import utils


class TestRandomPassword(unittest.TestCase):
    def test_random_password(self):
        for size in range(6, 24):
            assert len(utils.random_password(size=size)) == size


class TestExecute(unittest.TestCase):
    @patch('subprocess.Popen')
    def test_execute_success(self, Popen):
        command = ('command', 'arg1', 'arg2')
        optargs = {'stdout': 1, 'stderr': 2, 'cwd': '/path'}
        outputs = ('hello stdout', 'hello stderr')

        Popen.return_value.attach_mock(Mock(return_value=outputs),
                                       'communicate')

        ret = utils.execute(command, **optargs)

        Popen.assert_called_once_with(command, **optargs)
        assert ret == outputs
