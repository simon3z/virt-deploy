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
import libxml2
import netaddr
import os
import os.path
import subprocess

import virtdeploy

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


def _get_image_os(image):
    try:
        return _IMAGE_OS_TABLE[image]
    except KeyError:
        return image.replace('-', '')


def _create_base(template, arch, repository):
    name = '_{0}-{1}.{2}'.format(template, arch, BASE_FORMAT)
    path = os.path.join(repository, name)

    if not os.path.exists(path):
        execute(('virt-builder', template,
                 '-o', path,
                 '--size', BASE_SIZE,
                 '--format', BASE_FORMAT,
                 '--arch', arch,
                 '--root-password', 'locked:disabled'))

        # As mentioned in the virt-builder man in section "CLONES" the
        # resulting image should be cleaned before bsing used as template.
        # TODO: handle half-backed templates
        execute(('virt-sysprep', '-a', path))

    return name


def execute(args, stdout=None, stderr=None, cwd=None):
    p = subprocess.Popen(args, stdout=stdout, stderr=stderr, cwd=cwd)

    out, err = p.communicate()

    if p.returncode != 0:
        subprocess.CalledProcessError(p.returncode, args)

    return out, err


def _get_virt_templates():
    stdout, _ = execute(('virt-builder', '-l', '--list-format', 'json'),
                        stdout=subprocess.PIPE)
    return json.loads(stdout)


def template_list():
    templates = _get_virt_templates()

    if templates['version'] != 1:
        raise RuntimeError('Unsupported template list version')

    return [{'id': x['os-version'], 'name': x['full-name']}
            for x in templates['templates']]


def _libvirt_open(uri=None):
    def libvirt_callback(ctx, err):
        pass  # add logging only when required

    libvirt.registerErrorHandler(libvirt_callback, ctx=None)
    return libvirt.open(uri)


def instance_create(vmid, template, uri='', **kwargs):
    kwargs = dict(INSTANCE_DEFAULTS.items() + kwargs.items())

    name = '{0}-{1}-{2}'.format(vmid, template, kwargs['arch'])
    image = '{0}.qcow2'.format(name)

    conn = _libvirt_open(uri)
    pool = conn.storagePoolLookupByName(kwargs['pool'])
    net = conn.networkLookupByName(kwargs['network'])

    repository = _get_pool_path(pool)
    path = os.path.join(repository, image)

    if os.path.exists(path):
        raise OSError(os.errno.EEXIST, "Image already exists")

    base = _create_base(template, kwargs['arch'], repository)

    execute(('qemu-img', 'create', '-f', 'qcow2', '-b', base, image),
            cwd=repository)

    hostname = 'vm-{0}'.format(vmid)

    domainname = _get_network_domainname(net)

    if domainname is None:
        fqdn = hostname
    else:
        fqdn = '{0}.{1}'.format(hostname, domainname)

    if kwargs['password'] is None:
        kwargs['password'] = virtdeploy.random_password()

    execute(('virt-customize',
             '-a', path,
             '--hostname', fqdn,
             '--root-password', 'password:{0}'.format(kwargs['password'])))

    disk = 'path={0},format=qcow2,bus=scsi,discard=unmap'.format(path)
    network = 'network={0},filterref=clean-traffic'.format(kwargs['network'])
    channel = 'unix,name=org.qemu.guest_agent.0'

    execute(('virt-install',
             '--connect={0}'.format(uri),
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

    netmac = _get_domain_mac_addresses(conn.lookupByName(name)).next()
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


def instance_delete(name, uri=''):
    conn = _libvirt_open(uri)

    try:
        dom = conn.lookupByName(name)
    except libvirt.libvirtError as e:
        if e.get_error_code() != libvirt.VIR_ERR_NO_DOMAIN:
            raise
        return  ## nothing to do from here down

    xmldesc = libxml2.parseDoc(dom.XMLDesc())

    for disk in xmldesc.xpathEval('/domain/devices/disk/source'):
        os.remove(disk.prop('file'))

    netmacs = {}

    for x in _get_domain_mac_addresses(dom):
        netmacs.setdefault(x['network'], []).append(x['mac'])

    for network, macs in netmacs.iteritems():
        net = conn.networkLookupByName(network)

        for x in _get_network_dhcp_hosts(net):
            if x['mac'] in macs:
                _del_network_host(net, x['ip'])
                _del_network_dhcp_host(net, x['ip'])

    dom.undefine()


def _get_domain_mac_addresses(dom):
    xmldesc = libxml2.parseDoc(dom.XMLDesc())
    netxpath = '/domain/devices/interface[@type="network"]'

    for iface in xmldesc.xpathEval(netxpath):
        network = iface.xpathEval('./source')[0].prop('network')
        mac = iface.xpathEval('./mac')[0].prop('address')

        yield {'mac': mac, 'network': network}


def _get_pool_path(pool):
    xmldesc = libxml2.parseDoc(pool.XMLDesc())

    for x in xmldesc.xpathEval('/pool[@type="dir"]/target/path'):
        return x.getContent()

    raise OSError(os.errno.ENOENT, 'Path not found for pool')


def _get_network_domainname(net):
    xmldesc = libxml2.parseDoc(net.XMLDesc())

    for domain in xmldesc.xpathEval('/network/domain'):
        return domain.prop('name')


def _add_network_host(net, hostname, ipaddress):
    xmlhost = libxml2.newNode('host')
    xmlhost.newProp('ip', ipaddress)
    xmlhost.newChild(None, 'hostname', hostname)

    # Attempt to delete if present
    _del_network_host(net, ipaddress)
    net.update(_NET_ADD_LAST, _NET_DNS_HOST, 0, str(xmlhost),
               _NET_UPDATE_FLAGS)


def _del_network_host(net, ipaddress):
    xmlhost = libxml2.newNode('host')
    xmlhost.newProp('ip', ipaddress)

    try:
        net.update(_NET_DELETE, _NET_DNS_HOST, 0, str(xmlhost),
                   _NET_UPDATE_FLAGS)
    except libvirt.libvirtError as e:
        if e.get_error_code() != libvirt.VIR_ERR_OPERATION_INVALID:
            raise


def _add_network_dhcp_host(net, hostname, mac, ipaddress):
    xmlhost = libxml2.newNode('host')
    xmlhost.newProp('mac', mac)
    xmlhost.newProp('name', hostname)
    xmlhost.newProp('ip', ipaddress)

    net.update(_NET_ADD_LAST, _NET_DHCP_HOST, 0, str(xmlhost),
               _NET_UPDATE_FLAGS)


def _del_network_dhcp_host(net, ipaddress):
    xmlhost = libxml2.newNode('host')
    xmlhost.newProp('ip', ipaddress)

    try:
        net.update(_NET_DELETE, _NET_DHCP_HOST, 0, str(xmlhost),
                   _NET_UPDATE_FLAGS)
    except libvirt.libvirtError as e:
        if e.get_error_code() != libvirt.VIR_ERR_OPERATION_INVALID:
            raise


def _get_network_dhcp_hosts(net):
    xmldesc = libxml2.parseDoc(net.XMLDesc())

    for x in xmldesc.xpathEval('/network/ip/dhcp/host'):
        yield {'name': x.prop('name'), 'mac': x.prop('mac'),
               'ip': x.prop('ip')}


def _get_network_dhcp_leases(net):
    for x in _get_network_dhcp_hosts(net):
        yield x

    for x in net.DHCPLeases():
        yield {'name': x['hostname'], 'mac': x['mac'],
               'ip': x['ipaddr']}


def _new_network_ipaddress(net):
    xmldesc = libxml2.parseDoc(net.XMLDesc())

    hosts = _get_network_dhcp_leases(net)
    addresses = set(netaddr.IPAddress(x['ip']) for x in hosts)

    localip = xmldesc.xpathEval('/network/ip')[0].prop('address')
    netmask = xmldesc.xpathEval('/network/ip')[0].prop('netmask')

    addresses.add(netaddr.IPAddress(localip))

    for ip in netaddr.IPNetwork(localip, netmask)[1:-1]:
        if ip not in addresses:
            return str(ip)


def instance_address(name, uri='', network=DEFAULT_NET):
    conn = _libvirt_open(uri)

    hosts = _get_network_dhcp_leases(conn.networkLookupByName(network))
    addresses = dict((x['mac'], x['ip']) for x in hosts)

    macs = _get_domain_mac_addresses(conn.lookupByName(name))
    netmacs = filter(lambda x: x['network'] == network, macs)

    return filter(None, (addresses.get(x['mac']) for x in netmacs))
