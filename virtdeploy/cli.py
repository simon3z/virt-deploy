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
from __future__ import print_function

import argparse
import pkg_resources
import subprocess
import sys

import virtdeploy
from virtdeploy import errors
from virtdeploy import utils

DRIVER = 'libvirt'

EXITCODE_SUCCESS = 0
EXITCODE_FAILURE = 1
EXITCODE_TIMEOUT = 124
EXITCODE_KEYBINT = 130


def instance_create(args):
    driver = virtdeploy.get_driver(DRIVER)
    instance = driver.instance_create(args.id, args.template)

    print('name: {0}'.format(instance['name']))
    print('root password: {0}'.format(instance['password']))
    print('mac address: {0}'.format(instance['mac']))
    print('hostname: {0}'.format(instance['hostname']))
    print('ip address: {0}'.format(instance['ipaddress']))


def instance_start(args):
    driver = virtdeploy.get_driver(DRIVER)
    driver.instance_start(args.name)

    if args.wait:
        address_found = utils.wait_tcp_access(driver, args.name)
        if address_found is None:
            return EXITCODE_TIMEOUT

    return EXITCODE_SUCCESS


def instance_stop(args):
    driver = virtdeploy.get_driver(DRIVER)
    return driver.instance_stop(args.name)


def instance_delete(args):
    driver = virtdeploy.get_driver(DRIVER)
    return driver.instance_delete(args.name)


def template_list(args):
    driver = virtdeploy.get_driver(DRIVER)
    for template in driver.template_list():
        print(u'{0:24}{1:24}'.format(template['id'], template['name']))


def instance_address(args):
    driver = virtdeploy.get_driver(DRIVER)
    print('\n'.join(driver.instance_address(args.name)))


def command_ssh(args):
    driver = virtdeploy.get_driver(DRIVER)

    command = ['ssh', '-A',
               '-o', 'StrictHostKeychecking=no',
               '-o', 'UserKnownHostsFile=/dev/null',
               '-o', 'LogLevel=QUIET']

    user, _, name = args.name.rpartition('@')

    if user:
        command.extend(('-l', user))

    command.append(driver.instance_address(name)[0])
    command.extend(args.arguments)

    return subprocess.call(command)


COMMAND_TABLE = {
    'create': instance_create,
    'start': instance_start,
    'stop': instance_stop,
    'delete': instance_delete,
    'templates': template_list,
    'address': instance_address,
    'ssh': command_ssh,
}


def parse_command_line(cmdline):
    parser = argparse.ArgumentParser()

    version = pkg_resources.get_distribution('virt-deploy').version
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s {0}'.format(version))

    cmd = parser.add_subparsers(dest='command')

    cmd_create = cmd.add_parser('create', help='create a new instance')
    cmd_create.add_argument('id', help='new instance id')
    cmd_create.add_argument('template', help='template id')

    cmd_start = cmd.add_parser('start', help='start an instance')
    cmd_start.add_argument('--wait', action='store_true',
                           help='wait for ssh access availability')
    cmd_start.add_argument('name', help='name of instance to start')

    cmd_stop = cmd.add_parser('stop', help='stop an instance')
    cmd_stop.add_argument('name', help='name of instance to stop')

    cmd_delete = cmd.add_parser('delete', help='delete an instance')
    cmd_delete.add_argument('name', help='name of instance to delete')

    cmd.add_parser('templates', help='list all the templates')

    cmd_address = cmd.add_parser('address', help='instance ip address')
    cmd_address.add_argument('name', help='instance name')

    cmd_ssh = cmd.add_parser('ssh', help='connects to the instance')
    cmd_ssh.add_argument('name', help='instance name')
    cmd_ssh.add_argument('arguments', nargs='*', help='ssh arguments')

    args = parser.parse_args(args=cmdline)
    return COMMAND_TABLE[args.command](args)


def main():
    try:
        return parse_command_line(sys.argv[1:])
    except errors.VirtDeployException as e:
        print('error: {0}'.format(e), file=sys.stderr)
        raise SystemExit(EXITCODE_FAILURE)
    except KeyboardInterrupt:
        raise SystemExit(EXITCODE_KEYBINT)
