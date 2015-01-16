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
import virtdeploy


def instance_create(args):
    instance = virtdeploy.instance_create(args.id, args.template)

    print('name: {0}'.format(instance['name']))
    print('root password: {0}'.format(instance['password']))
    print('mac address: {0}'.format(instance['mac']))
    print('hostname: {0}'.format(instance['hostname']))
    print('ip address: {0}'.format(instance['ipaddress']))


def instance_delete(args):
    return virtdeploy.instance_delete(args.name)


def template_list(args):
    for template in virtdeploy.template_list():
        print(u'{0:24}{1:24}'.format(template['id'], template['name']))


def instance_address(args):
    print('\n'.join(virtdeploy.instance_address(args.name)))


COMMAND_TABLE = {
    'create': instance_create,
    'delete': instance_delete,
    'templates': template_list,
    'address': instance_address,
}


def main():
    parser = argparse.ArgumentParser()
    cmd = parser.add_subparsers(dest='command')

    cmd_create = cmd.add_parser('create', help='create a new instance')
    cmd_create.add_argument('id', help='new instance id')
    cmd_create.add_argument('template', help='template id')

    cmd_delete = cmd.add_parser('delete', help='delete an instance')
    cmd_delete.add_argument('name', help='name of instance to delete')

    cmd.add_parser('templates', help='list all the templates')

    cmd_address = cmd.add_parser('address', help='instance ip address')
    cmd_address.add_argument('name', help='instance name')

    args = parser.parse_args()

    try:
        return COMMAND_TABLE[args.command](args)
    except virtdeploy.errors.VirtDeployException as e:
        print('error: {0}'.format(e))
        return 1
