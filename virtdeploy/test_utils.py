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

from mock import MagicMock
from mock import call
from mock import patch
from socket import SOL_SOCKET
from socket import SO_ERROR
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


class TestMonotonicTime(unittest.TestCase):
    def test_monotonic_time(self):
        self.assertEqual(type(utils.monotonic_time()), float)


class TestWaitTcpAccess(unittest.TestCase):
    TIMEOUT = 180.0
    MININT = 5.0
    HALFMININT = MININT / 2.0
    MAXINT = 10.0

    EXERCISES = (
        {
            'monotime': [0, 0, 0, TIMEOUT],
            'probearg': [MAXINT],
            'proberet': [None],
            'retvalue': None,
            'sleepexp': [call(MININT)],
        },
        {
            'monotime': [0, 0, (MININT - HALFMININT), TIMEOUT],
            'probearg': [MAXINT],
            'proberet': [None],
            'retvalue': None,
            'sleepexp': [call(HALFMININT)],
        },
        {
            'monotime': [0, 0, MININT, TIMEOUT],
            'probearg': [MAXINT],
            'proberet': [None],
            'retvalue': None,
            'sleepexp': [call(0)],
        },
        {
            'monotime': [0, 0, (MININT + 1.0), TIMEOUT],
            'probearg': [MAXINT],
            'proberet': [None],
            'retvalue': None,
            'sleepexp': [call(0)],
        },
        {
            'monotime': [0, 0, (MININT - HALFMININT), (TIMEOUT - MININT),
                         (TIMEOUT - MININT + HALFMININT), TIMEOUT],
            'probearg': [MAXINT, MININT],
            'proberet': [None, None],
            'retvalue': None,
            'sleepexp': [call(HALFMININT)],
        },
        {
            'monotime': [0, 0, MININT, MAXINT],
            'probearg': [MAXINT],
            'proberet': [None, '192.168.122.2'],
            'retvalue': '192.168.122.2',
            'sleepexp': [call(0)],
        },
    )

    @patch('time.sleep')
    @patch('virtdeploy.utils.monotonic_time')
    @patch('virtdeploy.utils.probe_tcp_access')
    def test_wait_tcp_access(self, probe_mock, monotime_mock, sleep_mock):
        for exercise in self.EXERCISES:
            probe_mock.side_effect = exercise['proberet']
            monotime_mock.side_effect = exercise['monotime']

            retvalue = utils.wait_tcp_access(None, None,
                                             timeout=self.TIMEOUT,
                                             mininterval=self.MININT,
                                             maxinterval=self.MAXINT)

            probe_mock.called_with(timeout=exercise['probearg'])
            self.assertEqual(retvalue, exercise['retvalue'])
            self.assertEqual(sleep_mock.mock_calls, exercise['sleepexp'])

            sleep_mock.reset_mock()


class TestProbeTcpAccess(unittest.TestCase):
    TIMEOUT = 10

    def setUp(self):
        self.addresses = ['192.168.122.2', '192.168.122.3']
        self.sockets = [MagicMock() for _ in self.addresses]
        self.driver_mock = MagicMock()
        self.driver_mock.instance_address.return_value = self.addresses

    @patch('select.select')
    @patch('socket.socket')
    @patch('virtdeploy.utils.monotonic_time')
    def test_probe_timeout(self, time_mock, socket_mock, select_mock):
        socket_mock.side_effect = self.sockets
        time_mock.side_effect = [0, 0, self.TIMEOUT / 2, self.TIMEOUT]
        select_mock.return_value = (), (), ()

        retvalue = utils.probe_tcp_access(self.driver_mock, None,
                                          timeout=self.TIMEOUT)

        self.assertEqual(retvalue, None)

        self._assert_sockets_calls()

        # FIXME: mock should record the collection snapshot, not the
        # collection object, code should be:
        #   call((), self.sockets, (), self.TIMEOUT)
        select_mock.assert_has_calls([
            call((), [], (), self.TIMEOUT),
            call((), [], (), self.TIMEOUT / 2),
        ])

    @patch('select.select')
    @patch('socket.socket')
    @patch('virtdeploy.utils.monotonic_time')
    def test_probe_success(self, time_mock, socket_mock, select_mock):
        sock = self.sockets[0]

        sock.getsockopt.return_value = 0
        sock.getpeername.return_value = self.addresses[0]

        socket_mock.side_effect = self.sockets
        time_mock.side_effect = [0, 0]
        select_mock.return_value = (), (sock,), ()

        retvalue = utils.probe_tcp_access(self.driver_mock, None,
                                          timeout=self.TIMEOUT)

        self.assertEqual(retvalue, self.addresses[0])

        self._assert_sockets_calls()

        sock.getsockopt.assert_called_with(SOL_SOCKET, SO_ERROR)

    def _assert_sockets_calls(self):
        for sock, address in zip(self.sockets, self.addresses):
            sock.setblocking.assert_called_once_with(0)
            sock.connect_ex.assert_called_once_with((address, 22))
            sock.close.assert_called_once_with()
