Easily Deploy Virtual Machines
==============================

.. image:: https://travis-ci.org/simon3z/virt-deploy.svg
          :target: https://travis-ci.org/simon3z/virt-deploy

.. image:: https://coveralls.io/repos/simon3z/virt-deploy/badge.svg
        :target: https://coveralls.io/r/simon3z/virt-deploy

Virt-deploy is a python library to standardize the deployment of virtual
machines.  It currently supports libvirt_ and takes advantage of virt-builder_
and virt-install_ to automate the creation of templates and instances.

.. _libvirt: http://libvirt.org
.. _virt-builder: http://libguestfs.org/virt-builder.1.html
.. _virt-install: http://virt-manager.org

::

  usage: virt-deploy [-h] [-v]
                     {create,start,stop,delete,templates,address,ssh} ...

  positional arguments:
    {create,start,stop,delete,templates,address,ssh}
      create              create a new instance
      start               start an instance
      stop                stop an instance
      delete              delete an instance
      templates           list all the templates
      address             instance ip address
      ssh                 connects to the instance

  optional arguments:
    -h, --help            show this help message and exit
    -v, --version         show program's version number and exit


Creation of an Instance
=======================
To create a new vm instance based on a fedora-21 template:

::

  # virt-deploy create instance01 fedora-21

The fedora-21 template image will be downloaded (virt-builder), and prepared
to be used (virt-sysprep). This is done only once when the template is used
for the first time.

The instance is then created with some customization such as random root
password and the hostname. All the information are then summarized when
the creation is completed:

::

  name: vm-test01-fedora-21-x86_64
  root password: xxxxxxxxxx
  mac address: 52:54:00:xx:xx:xx
  hostname: vm-test01
  ip address: 192.168.122.xxx


Storage and Network Management
==============================

Virt-deploy uses the 'default' libvirt storage pool and network. Images are
created in the pool path and hostnames and ip addresses are assigned and
registered in the network definition.


Building from Sources
=====================

At the moment the suggested procedure to build from sources is to produce
rpms with the proper packages requirements (virt-builder and virt-install):

::

  $ python setup.py sdist
  $ sudo dnf builddep virt-deploy.spec
  $ rpmbuild -ta dist/virt-deploy-<version>.tar.gz

If you're a yum user (centos and fedora < 21) then you should use yum
instead of dnf:

::

  $ sudo yum-builddep virt-deploy.spec
