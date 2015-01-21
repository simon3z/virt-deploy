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

import random
import string
import subprocess

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
