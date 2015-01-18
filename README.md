# Easily Deploy Virtual Machines

![Build Status](https://travis-ci.org/simon3z/virt-deploy.svg?branch=master)
![Coverage Status](https://coveralls.io/repos/simon3z/virt-deploy/badge.svg?branch=master)

Virt-deploy is a python library to standardize the deployment of virtual machines.
It currently supports [libvirt](http://libvirt.org) and takes advantage of
[virt-builder](http://libguestfs.org/virt-builder.1.html]) and
[virt-install](http://virt-manager.org) to automate the creation of templates and
instances.


    usage: virt-deploy [-h] {create,templates,address} ...

    positional arguments:
      {create,templates,address}
        create              create a new instance
        templates           list all the templates
        address             instance ip address

    optional arguments:
      -h, --help            show this help message and exit


## Creation of an Instance

To create a new vm instance based on a fedora-21 template:

    # virt-deploy create instance01 fedora-21

The fedora-21 template image will be downloaded (virt-builder), and prepared
to be used (virt-sysprep). This is done only once when the template is used
for the first time.

The instance is then created with some costumization such as random root
password and the hostname. All the information are then summarized when
the creation is completed:

    name: vm-test01-fedora-21-x86_64
    root password: xxxxxxxxxx
    mac address: 52:54:00:xx:xx:xx
    hostname: vm-test01
    ip address: 192.168.122.xxx


## Storage and Network Management

Virt-deploy uses the 'default' libvirt storage pool and network. Images are
created in the pool path and hostnames and ip addresses are assigned and
registered in the network definition.
