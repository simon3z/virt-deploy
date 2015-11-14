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
import inspect
import unittest

from mock import patch

from . import get_driver
from . import get_driver_class
from . import get_driver_names

from .driverbase import VirtDeployDriverBase
from .drivers import test_libvirt


class TestVirtDeployDriverBase(unittest.TestCase):
    def _get_driver_methods(self):
        return inspect.getmembers(VirtDeployDriverBase, inspect.ismethod)

    def _get_driver_class(self, name):
        with patch.dict(sys.modules, {'libvirt': test_libvirt.libvirt_mock}):
            return get_driver_class(name)

    def _get_driver(self, name):
        with patch.dict(sys.modules, {'libvirt': test_libvirt.libvirt_mock}):
            return get_driver(name)

    def test_base_not_implemented(self):
        driver = VirtDeployDriverBase()

        for name, method in self._get_driver_methods():
            spec = inspect.getargspec(method)

            with self.assertRaises(NotImplementedError) as cm:
                getattr(driver, name)(*(None,) * (len(spec.args) - 1))

            self.assertEqual(cm.exception.args[0], name)

    def test_drivers_interface(self):
        for driver_name in get_driver_names():
            driver = self._get_driver_class(driver_name)

            for name, method in self._get_driver_methods():
                driver_method = getattr(driver, name)
                self.assertNotEqual(driver_method, method)
                self.assertEqual(inspect.getargspec(method),
                                 inspect.getargspec(driver_method))

    def test_get_drivers(self):
        for driver_name in get_driver_names():
            driver = self._get_driver(driver_name)
            self.assertTrue(isinstance(driver, VirtDeployDriverBase))
