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

from setuptools import find_packages
from setuptools import setup


setup(
    name='virt-deploy',
    description='Standardized deployment of virtual machines',
    author='Federico Simoncelli',
    author_email='fsimonce@redhat.com',
    url='https://github.com/simon3z/virt-deploy',
    version='0.1.8',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'virt-deploy = virtdeploy.cli:main',
        ]
    },
)
