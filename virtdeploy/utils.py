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

import os
import random
import select
import socket
import string
import subprocess
import time

_PASSWORD_CHARS = string.ascii_letters + string.digits + '!#$%&'


def execute(args, stdout=None, stderr=None, cwd=None):
    p = subprocess.Popen(args, stdout=stdout, stderr=stderr, cwd=cwd)

    out, err = p.communicate()

    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, args)

    return out, err


def random_password(size=12):
    chars = (random.choice(_PASSWORD_CHARS) for _ in range(size))
    return ''.join(chars)


def monotonic_time():
    return os.times()[4]


def probe_tcp_access(driver, vmid, port=22, timeout=10):
    sockets = list()
    endtime = monotonic_time() + timeout

    for address in driver.instance_address(vmid):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)
        sock.connect_ex((address, port))
        sockets.append(sock)

    address_found = None

    while sockets and address_found is None:
        remaining = endtime - monotonic_time()

        if remaining <= 0:
            break

        _, response, _ = select.select((), sockets, (), remaining)

        for sock in response:
            e = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)

            if e == 0:
                address_found = sock.getpeername()

            sock.close()
            sockets.remove(sock)

    for sock in list(sockets):
        sock.close()
        sockets.remove(sock)

    return address_found


def wait_tcp_access(driver, vmid, port=22, timeout=180,
                    mininterval=5.0, maxinterval=10.0):
    endtime = monotonic_time() + timeout

    while True:
        probetime = monotonic_time()
        remaining = min(maxinterval, endtime - probetime)

        if remaining <= 0:
            return None

        address_found = probe_tcp_access(driver, vmid, port, remaining)

        if address_found is not None:
            return address_found

        nexttry = probetime + mininterval

        if nexttry >= endtime:
            return None

        time.sleep(max(0, nexttry - monotonic_time()))
