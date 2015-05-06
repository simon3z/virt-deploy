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

import json
import libvirt
import netaddr
import os
import os.path
import subprocess

from lxml import etree

from ..driverbase import VirtDeployDriverBase
from ..errors import InstanceNotFound
from ..errors import VirtDeployException
from ..utils import execute
from ..utils import random_password

DEFAULT_NET = 'default'
DEFAULT_POOL = 'default'

BASE_FORMAT = 'qcow2'
BASE_SIZE = '20G'

INSTANCE_DEFAULTS = {
    'cpus': 2,
    'memory': 1024,
    'arch': 'x86_64',
    'network': DEFAULT_NET,
    'pool': DEFAULT_POOL,
    'password': None,
    'clone': True,
}

_NET_ADD_LAST = libvirt.VIR_NETWORK_UPDATE_COMMAND_ADD_LAST
_NET_MODIFY = libvirt.VIR_NETWORK_UPDATE_COMMAND_MODIFY
_NET_DELETE = libvirt.VIR_NETWORK_UPDATE_COMMAND_DELETE
_NET_DNS_HOST = libvirt.VIR_NETWORK_SECTION_DNS_HOST
_NET_DHCP_HOST = libvirt.VIR_NETWORK_SECTION_IP_DHCP_HOST
_NET_UPDATE_FLAGS = (
    libvirt.VIR_NETWORK_UPDATE_AFFECT_CONFIG |
    libvirt.VIR_NETWORK_UPDATE_AFFECT_LIVE
)

_IMAGE_OS_TABLE = {
    'centos-6': 'centos6.5',  # TODO: fix versions
    'centos-7.0': 'centos7.0',
}


class VirtDeployLibvirtDriver(VirtDeployDriverBase):
    def __init__(self, uri='qemu:///system'):
        self._uri = uri

    def _libvirt_open(self):
        def libvirt_callback(ctx, err):
            pass  # add logging only when required

        libvirt.registerErrorHandler(libvirt_callback, ctx=None)
        return libvirt.open(self._uri)

    def template_list(self):
        templates = _get_virt_templates()

        if templates['version'] != 1:
            raise VirtDeployException('Unsupported template list version')

        return [{'id': x['os-version'], 'name': x['full-name']}
                for x in templates['templates']]

    def instance_create(self, vmid, template, **kwargs):
        kwargs = dict(INSTANCE_DEFAULTS.items() + kwargs.items())

        name = '{0}-{1}-{2}'.format(vmid, template, kwargs['arch'])
        image = '{0}.qcow2'.format(name)

        conn = self._libvirt_open()
        pool = conn.storagePoolLookupByName(kwargs['pool'])
        net = conn.networkLookupByName(kwargs['network'])

        path = os.path.join(_get_pool_path(pool), image)

        if os.path.exists(path):
            raise OSError(os.errno.EEXIST, "Image already exists")

        if kwargs['clone']:
            # TODO: add ability to configure the size
            _create_clone(path, template, kwargs['arch'], BASE_SIZE)
        else:
            _create_thinp(path, template, kwargs['arch'], BASE_SIZE)

        hostname = 'vm-{0}'.format(vmid)
        domainname = _get_network_domainname(net)

        if domainname is None:
            fqdn = hostname
        else:
            fqdn = '{0}.{1}'.format(hostname, domainname)

        if kwargs['password'] is None:
            kwargs['password'] = random_password()

        password_string = 'password:{0}'.format(kwargs['password'])

        execute(('virt-customize',
                 '-a', path,
                 '--hostname', fqdn,
                 '--root-password', password_string))

        network = 'network={0}'.format(kwargs['network'])

        try:
            conn.nwfilterLookupByName('clean-traffic')
        except libvirt.libvirtError as e:
            if e.get_error_code() != libvirt.VIR_ERR_NO_NWFILTER:
                raise
        else:
            network += ',filterref=clean-traffic'

        disk = 'path={0},format=qcow2,bus=scsi,discard=unmap'.format(path)
        channel = 'unix,name=org.qemu.guest_agent.0'

        execute(('virt-install',
                 '--quiet',
                 '--connect={0}'.format(self._uri),
                 '--name', name,
                 '--cpu', 'host-model-only,+vmx',
                 '--vcpus', str(kwargs['cpus']),
                 '--memory', str(kwargs['memory']),
                 '--controller', 'scsi,model=virtio-scsi',
                 '--disk', disk,
                 '--network', network,
                 '--graphics', 'spice',
                 '--channel', channel,
                 '--os-variant', _get_image_os(template),
                 '--import',
                 '--noautoconsole',
                 '--noreboot'))

        netmac = _get_domain_mac_addresses(_get_domain(conn, name)).next()
        ipaddress = _new_network_ipaddress(net)

        # TODO: fix race between _new_network_ipaddress and ip reservation
        _add_network_host(net, hostname, ipaddress)
        _add_network_dhcp_host(net, hostname, netmac['mac'], ipaddress)

        return {
            'name': name,
            'password': kwargs['password'],
            'mac': netmac['mac'],
            'hostname': fqdn,
            'ipaddress': ipaddress,
        }

    def instance_address(self, vmid, network=None):
        conn = self._libvirt_open()
        dom = _get_domain(conn, vmid)

        netmacs = _get_domain_macs_by_network(dom)

        if network:
            netmacs = {k: v for k, v in netmacs.iteritems()}

        addresses = set()

        for name, macs in netmacs.iteritems():
            net = conn.networkLookupByName(name)

            for lease in _get_network_dhcp_leases(net):
                if lease['mac'] in macs:
                    addresses.add(lease['ip'])

        return list(addresses)

    def instance_start(self, vmid):
        dom = _get_domain(self._libvirt_open(), vmid)

        try:
            dom.create()
        except libvirt.libvirtError as e:
            if e.get_error_code() != libvirt.VIR_ERR_OPERATION_INVALID:
                raise

    def instance_stop(self, vmid):
        dom = _get_domain(self._libvirt_open(), vmid)

        try:
            dom.shutdownFlags(
                libvirt.VIR_DOMAIN_SHUTDOWN_GUEST_AGENT |
                libvirt.VIR_DOMAIN_SHUTDOWN_ACPI_POWER_BTN
            )
        except libvirt.libvirtError as e:
            if e.get_error_code() != libvirt.VIR_ERR_OPERATION_INVALID:
                raise

    def instance_delete(self, vmid):
        conn = self._libvirt_open()
        dom = _get_domain(conn, vmid)

        try:
            dom.destroy()
        except libvirt.libvirtError as e:
            if e.get_error_code() != libvirt.VIR_ERR_OPERATION_INVALID:
                raise

        xmldesc = etree.fromstring(dom.XMLDesc())

        for disk in xmldesc.iterfind('./devices/disk/source'):
            try:
                os.remove(disk.get('file'))
            except OSError as e:
                if e.errno != os.errno.ENOENT:
                    raise

        netmacs = _get_domain_macs_by_network(dom)

        for network, macs in netmacs.iteritems():
            net = conn.networkLookupByName(network)

            for x in _get_network_dhcp_hosts(net):
                if x['mac'] in macs:
                    _del_network_host(net, x['name'])
                    _del_network_dhcp_host(net, x['name'])

        dom.undefineFlags(libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA)


def _get_image_os(image):
    try:
        return _IMAGE_OS_TABLE[image]
    except KeyError:
        return image.replace('-', '')


def _create_clone(path, template, arch, size):
    if os.path.exists(path):
        raise OSError(os.errno.EEXIST, "Image already exists")

    execute(('virt-builder', template,
             '-o', path,
             '--size', size,
             '--format', BASE_FORMAT,
             '--arch', arch,
             '--root-password', 'locked:disabled'))


def _create_thinp(path, template, arch, size):
    image = os.path.basename(path)
    repository = os.path.dirname(path)

    name = '_{0}-{1}.{2}'.format(template, arch, BASE_FORMAT)
    path = os.path.join(repository, name)

    if not os.path.exists(path):
        _create_clone(path, template, arch, size, BASE_FORMAT)

        # As mentioned in the virt-builder man in section "CLONES" the
        # resulting image should be cleaned before bsing used as template.
        # TODO: handle half-backed templates
        execute(('virt-sysprep', '-a', path))

    execute(('qemu-img', 'create', '-f', 'qcow2', '-b', name, image),
            cwd=repository)

    return name


def _get_virt_templates():
    stdout, _ = execute(('virt-builder', '-l', '--list-format', 'json'),
                        stdout=subprocess.PIPE)
    return json.loads(stdout)


def _get_domain(conn, name):
    try:
        return conn.lookupByName(name)
    except libvirt.libvirtError as e:
        if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
            raise InstanceNotFound(name)
        raise


def _get_domain_mac_addresses(dom):
    xmldesc = etree.fromstring(dom.XMLDesc())
    netxpath = './devices/interface[@type="network"]'

    for iface in xmldesc.iterfind(netxpath):
        network = iface.find('./source').get('network')
        mac = iface.find('./mac').get('address')

        yield {'mac': mac, 'network': network}


def _get_domain_macs_by_network(dom):
    netmacs = {}

    for x in _get_domain_mac_addresses(dom):
        netmacs.setdefault(x['network'], []).append(x['mac'])

    return netmacs


def _get_pool_path(pool):
    xmldesc = etree.fromstring(pool.XMLDesc())

    for x in xmldesc.iterfind('.[@type="dir"]/target/path'):
        return x.text

    raise OSError(os.errno.ENOENT, 'Path not found for pool')


def _get_network_domainname(net):
    xmldesc = etree.fromstring(net.XMLDesc())

    for domain in xmldesc.iterfind('./domain'):
        return domain.get('name')


def _add_network_host(net, hostname, ipaddress):
    xmlhost = etree.Element('host')
    xmlhost.set('ip', ipaddress)
    etree.SubElement(xmlhost, 'hostname').text = hostname

    # Attempt to delete if present
    _del_network_host(net, hostname)
    net.update(_NET_ADD_LAST, _NET_DNS_HOST, 0, etree.tostring(xmlhost),
               _NET_UPDATE_FLAGS)


def _del_network_host(net, hostname):
    xmlhost = etree.Element('host')
    etree.SubElement(xmlhost, 'hostname').text = hostname

    try:
        net.update(_NET_DELETE, _NET_DNS_HOST, 0, etree.tostring(xmlhost),
                   _NET_UPDATE_FLAGS)
    except libvirt.libvirtError as e:
        if e.get_error_code() != libvirt.VIR_ERR_OPERATION_INVALID:
            raise


def _add_network_dhcp_host(net, hostname, mac, ipaddress):
    xmlhost = etree.Element('host')
    xmlhost.set('mac', mac)
    xmlhost.set('name', hostname)
    xmlhost.set('ip', ipaddress)

    # Attempt to delete if present
    _del_network_dhcp_host(net, hostname)
    net.update(_NET_ADD_LAST, _NET_DHCP_HOST, 0, etree.tostring(xmlhost),
               _NET_UPDATE_FLAGS)


def _del_network_dhcp_host(net, hostname):
    xmlhost = etree.Element('host')
    xmlhost.set('name', hostname)

    try:
        net.update(_NET_DELETE, _NET_DHCP_HOST, 0, etree.tostring(xmlhost),
                   _NET_UPDATE_FLAGS)
    except libvirt.libvirtError as e:
        if e.get_error_code() != libvirt.VIR_ERR_OPERATION_INVALID:
            raise


def _get_network_dhcp_hosts(net):
    xmldesc = etree.fromstring(net.XMLDesc())

    for x in xmldesc.iterfind('./ip/dhcp/host'):
        yield {'name': x.get('name'), 'mac': x.get('mac'),
               'ip': x.get('ip')}


def _get_network_dhcp_leases(net):
    for x in _get_network_dhcp_hosts(net):
        yield x

    for x in net.DHCPLeases():
        yield {'name': x['hostname'], 'mac': x['mac'],
               'ip': x['ipaddr']}


def _new_network_ipaddress(net):
    xmldesc = etree.fromstring(net.XMLDesc())

    hosts = _get_network_dhcp_leases(net)
    addresses = set(netaddr.IPAddress(x['ip']) for x in hosts)

    localip = xmldesc.find('./ip').get('address')
    netmask = xmldesc.find('./ip').get('netmask')

    addresses.add(netaddr.IPAddress(localip))

    for ip in netaddr.IPNetwork(localip, netmask)[1:-1]:
        if ip not in addresses:
            return str(ip)
