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

import argparse
import sys

import virtdeploy
import virtdeploy.errors

DRIVER = 'libvirt'


def instance_create(args):
    driver = virtdeploy.get_deployment_driver(DRIVER)
    instance = driver.instance_create(args.id, args.template)

    print('name: {0}'.format(instance['name']))
    print('root password: {0}'.format(instance['password']))
    print('mac address: {0}'.format(instance['mac']))
    print('hostname: {0}'.format(instance['hostname']))
    print('ip address: {0}'.format(instance['ipaddress']))


def instance_start(args):
    driver = virtdeploy.get_deployment_driver(DRIVER)
    return driver.instance_start(args.name)


def instance_stop(args):
    driver = virtdeploy.get_deployment_driver(DRIVER)
    return driver.instance_stop(args.name)


def instance_delete(args):
    driver = virtdeploy.get_deployment_driver(DRIVER)
    return driver.instance_delete(args.name)


def template_list(args):
    driver = virtdeploy.get_deployment_driver(DRIVER)
    for template in driver.template_list():
        print(u'{0:24}{1:24}'.format(template['id'], template['name']))


def instance_address(args):
    driver = virtdeploy.get_deployment_driver(DRIVER)
    print('\n'.join(driver.instance_address(args.name)))


COMMAND_TABLE = {
    'create': instance_create,
    'start': instance_start,
    'stop': instance_stop,
    'delete': instance_delete,
    'templates': template_list,
    'address': instance_address,
}


def parse_command_line(cmdline):
    parser = argparse.ArgumentParser()
    cmd = parser.add_subparsers(dest='command')

    cmd_create = cmd.add_parser('create', help='create a new instance')
    cmd_create.add_argument('id', help='new instance id')
    cmd_create.add_argument('template', help='template id')

    cmd_start = cmd.add_parser('start', help='start an instance')
    cmd_start.add_argument('name', help='name of instance to start')

    cmd_stop = cmd.add_parser('stop', help='stop an instance')
    cmd_stop.add_argument('name', help='name of instance to stop')

    cmd_delete = cmd.add_parser('delete', help='delete an instance')
    cmd_delete.add_argument('name', help='name of instance to delete')

    cmd.add_parser('templates', help='list all the templates')

    cmd_address = cmd.add_parser('address', help='instance ip address')
    cmd_address.add_argument('name', help='instance name')

    args = parser.parse_args(args=cmdline)
    return COMMAND_TABLE[args.command](args)


def main():
    try:
        return parse_command_line(sys.argv[1:])
    except virtdeploy.errors.VirtDeployException as e:
        print('error: {0}'.format(e))
        raise SystemExit(1)
