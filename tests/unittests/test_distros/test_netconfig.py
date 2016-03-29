import copy
import os

try:
    from unittest import mock
except ImportError:
    import mock
try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from six import StringIO
from ..helpers import TestCase

from cloudinit import distros
from cloudinit import helpers
from cloudinit import settings
from cloudinit import util

from cloudinit.distros.parsers.sys_conf import SysConf


BASE_NET_CFG = '''
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address 192.168.1.5
    netmask 255.255.255.0
    network 192.168.0.0
    broadcast 192.168.1.0
    gateway 192.168.1.254

auto eth1
iface eth1 inet dhcp
'''

BASE_NET_CFG_IPV6 = '''
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address 192.168.1.5
    netmask 255.255.255.0
    network 192.168.0.0
    broadcast 192.168.1.255
    gateway 192.168.1.254

iface eth0 inet6 static
    address 2607:f0d0:1002:0011::2/64
    netmask 64
    gateway 2607:f0d0:1002:0011::1

iface eth1 inet static
    address 192.168.1.6
    netmask 255.255.255.0
    network 192.168.0.0
    broadcast 192.168.1.255
    gateway 192.168.1.254

iface eth1 inet6 static
    address 2607:f0d0:1002:0011::3/64
    netmask 64
    gateway 2607:f0d0:1002:0011::1
'''

BASE_NET_CFG_IPV6_JSON = {
    'lo': {'auto': True, 'ipv6': {}}, 'eth0': {'auto': True, 'address': '192.168.1.5', 'dns-nameservers': [], 'gateway': '192.168.1.254', 'broadcast': '192.168.1.255', 'netmask': '255.255.255.0', 'bootproto': 'static', 'ipv6': {'address': '2607:f0d0:1002:0011::2/64', 'secondaries': [], 'dns-nameservers': [], 'gateway': '2607:f0d0:1002:0011::1'}, 'inet6': True}, 'eth1': {'auto': False, 'ipv6': {'gateway': '2607:f0d0:1002:0011::1', 'secondaries': [], 'dns-nameservers': [], 'address': '2607:f0d0:1002:0011::3/64'}, 'dns-nameservers': [], 'inet6': True, 'broadcast': '192.168.1.255', 'netmask': '255.255.255.0', 'bootproto': 'static', 'address': '192.168.1.6', 'gateway': '192.168.1.254'}}


class WriteBuffer(object):
    def __init__(self):
        self.buffer = StringIO()
        self.mode = None
        self.omode = None

    def write(self, text):
        self.buffer.write(text)

    def __str__(self):
        return self.buffer.getvalue()


class TestNetCfgDistro(TestCase):

    def _get_distro(self, dname):
        cls = distros.fetch(dname)
        cfg = settings.CFG_BUILTIN
        cfg['system_info']['distro'] = dname
        paths = helpers.Paths({})
        return cls(dname, cfg, paths)

    def test_simple_write_ub(self):
        ub_distro = self._get_distro('ubuntu')
        with ExitStack() as mocks:
            write_bufs = {}

            def replace_write(filename, content, mode=0o644, omode="wb"):
                buf = WriteBuffer()
                buf.mode = mode
                buf.omode = omode
                buf.write(content)
                write_bufs[filename] = buf

            mocks.enter_context(
                mock.patch.object(util, 'write_file', replace_write))
            mocks.enter_context(
                mock.patch.object(os.path, 'isfile', return_value=False))

            ub_distro.apply_network(BASE_NET_CFG, False)

            self.assertEquals(len(write_bufs), 1)
            self.assertIn('/etc/network/interfaces', write_bufs)
            write_buf = write_bufs['/etc/network/interfaces']
            self.assertEquals(str(write_buf).strip(), BASE_NET_CFG.strip())
            self.assertEquals(write_buf.mode, 0o644)

    def assertCfgEquals(self, blob1, blob2):
        b1 = dict(SysConf(blob1.strip().splitlines()))
        b2 = dict(SysConf(blob2.strip().splitlines()))
        self.assertEquals(b1, b2)
        for (k, v) in b1.items():
            self.assertIn(k, b2)
        for (k, v) in b2.items():
            self.assertIn(k, b1)
        for (k, v) in b1.items():
            self.assertEquals(v, b2[k])

    def test_simple_write_rh(self):
        rh_distro = self._get_distro('rhel')
        rh_distro._detect_active_device = mock.MagicMock(return_value='eth0')

        write_bufs = {}

        def replace_write(filename, content, mode=0o644, omode="wb"):
            buf = WriteBuffer()
            buf.mode = mode
            buf.omode = omode
            buf.write(content)
            write_bufs[filename] = buf

        with ExitStack() as mocks:
            mocks.enter_context(
                mock.patch.object(util, 'write_file', replace_write))
            mocks.enter_context(
                mock.patch.object(util, 'load_file', return_value=''))
            mocks.enter_context(
                mock.patch.object(os.path, 'isfile', return_value=False))

            rh_distro.apply_network(BASE_NET_CFG, False)

            self.assertEquals(len(write_bufs), 4)
            self.assertIn('/etc/sysconfig/network-scripts/ifcfg-lo',
                          write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network-scripts/ifcfg-lo']
            expected_buf = '''
DEVICE="lo"
ONBOOT=yes
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)

            self.assertIn('/etc/sysconfig/network-scripts/ifcfg-eth0',
                          write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network-scripts/ifcfg-eth0']
            expected_buf = '''
DEVICE="eth0"
BOOTPROTO="static"
NETMASK="255.255.255.0"
IPADDR="192.168.1.5"
ONBOOT=yes
GATEWAY="192.168.1.254"
BROADCAST="192.168.1.0"
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)

            self.assertIn('/etc/sysconfig/network-scripts/ifcfg-eth1',
                          write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network-scripts/ifcfg-eth1']
            expected_buf = '''
DEVICE="eth1"
BOOTPROTO="dhcp"
ONBOOT=yes
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)

            self.assertIn('/etc/sysconfig/network', write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network']
            expected_buf = '''
# Created by cloud-init v. 0.7
NETWORKING=yes
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)

    def _test_rhel_subif_and_ipv6_json(self, nw_cfg):
        rh_distro = self._get_distro('rhel')
        rh_distro._detect_active_device = mock.MagicMock(return_value='eth0')

        write_bufs = {}

        def replace_write(filename, content, mode=0o644, omode="wb"):
            buf = WriteBuffer()
            buf.mode = mode
            buf.omode = omode
            buf.write(content)
            write_bufs[filename] = buf

        with ExitStack() as mocks:
            mocks.enter_context(
                mock.patch.object(util, 'write_file', replace_write))
            mocks.enter_context(
                mock.patch.object(util, 'load_file', return_value=''))
            mocks.enter_context(
                mock.patch.object(os.path, 'isfile', return_value=False))
            mocks.enter_context(
                mock.patch.object(os.path, 'isfile', return_value=False))

            rh_distro.apply_network(nw_cfg, False, True)

            self.assertEquals(len(write_bufs), 4)
            self.assertIn('/etc/sysconfig/network-scripts/ifcfg-lo',
                          write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network-scripts/ifcfg-lo']
            expected_buf = '''
DEVICE="lo"
ONBOOT=yes
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)

            self.assertIn('/etc/sysconfig/network-scripts/ifcfg-eth0',
                          write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network-scripts/ifcfg-eth0']
            expected_buf = '''
DEVICE="eth0"
BOOTPROTO="static"
NETMASK="255.255.255.0"
IPADDR="192.168.1.5"
ONBOOT=yes
GATEWAY="192.168.1.254"
BROADCAST="192.168.1.255"
IPV6INIT=yes
IPV6ADDR="2607:f0d0:1002:0011::2/64"
IPV6_DEFAULTGW="2607:f0d0:1002:0011::1"
IPV6ADDR_SECONDARIES="2607:f0d0:1002:0011::3/64"
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)
            self.assertIn('/etc/sysconfig/network-scripts/ifcfg-eth0:1',
                          write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network-scripts/ifcfg-eth0:1']
            expected_buf = '''
DEVICE="eth0:1"
BOOTPROTO="static"
NETMASK="255.255.255.0"
IPADDR="192.168.1.6"
ONBOOT=no
GATEWAY="192.168.1.254"
BROADCAST="192.168.1.255"
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)

            self.assertIn('/etc/sysconfig/network', write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network']
            expected_buf = '''
# Created by cloud-init v. 0.7
NETWORKING=yes
NETWORKING_IPV6=yes
IPV6_AUTOCONF=no
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)

    def test_rhel_active_interface_replacement(self):
        subif_ipv6_sec = copy.deepcopy(BASE_NET_CFG_IPV6_JSON)
        # replace eth0 with eth6, eth1 with eth6:1
        subif_ipv6_sec['eth6'] = subif_ipv6_sec['eth0']
        subif_ipv6_sec['eth6:1'] = subif_ipv6_sec['eth1']
        del subif_ipv6_sec['eth0']
        del subif_ipv6_sec['eth1']
        del subif_ipv6_sec['eth6:1']['ipv6']
        subif_ipv6_sec['eth6:1']['inet6'] = False
        subif_ipv6_sec['eth6']['ipv6']['secondaries'] = ['2607:f0d0:1002:0011::3/64']

        self._test_rhel_subif_and_ipv6_json(subif_ipv6_sec)

    def test_rhel_subif_and_ipv6_secondary(self):
        subif_ipv6_sec = copy.deepcopy(BASE_NET_CFG_IPV6_JSON)
        # replace eth1 with eth0:1, for subif
        subif_ipv6_sec['eth0:1'] = subif_ipv6_sec['eth1']
        del subif_ipv6_sec['eth1']
        del subif_ipv6_sec['eth0:1']['ipv6']
        subif_ipv6_sec['eth0:1']['inet6'] = False

        # populate ipv6 secondary for eth0
        subif_ipv6_sec['eth0']['ipv6']['secondaries'] = ['2607:f0d0:1002:0011::3/64']

        self._test_rhel_subif_and_ipv6_json(subif_ipv6_sec)

    def test_write_ipv6_rhel(self):
        self._test_write_ipv6_rhel(BASE_NET_CFG_IPV6, False)

    def test_write_ipv6_rhel_json(self):
        self._test_write_ipv6_rhel(BASE_NET_CFG_IPV6_JSON, True)

    def _test_write_ipv6_rhel(self, nw_cfg, is_json=False):
        rh_distro = self._get_distro('rhel')
        rh_distro._detect_active_device = mock.MagicMock(return_value='eth0')

        write_bufs = {}

        def replace_write(filename, content, mode=0o644, omode="wb"):
            buf = WriteBuffer()
            buf.mode = mode
            buf.omode = omode
            buf.write(content)
            write_bufs[filename] = buf

        with ExitStack() as mocks:
            mocks.enter_context(
                mock.patch.object(util, 'write_file', replace_write))
            mocks.enter_context(
                mock.patch.object(util, 'load_file', return_value=''))
            mocks.enter_context(
                mock.patch.object(os.path, 'isfile', return_value=False))
            mocks.enter_context(
                mock.patch.object(os.path, 'isfile', return_value=False))

            rh_distro.apply_network(nw_cfg, False, is_json)

            self.assertEquals(len(write_bufs), 4)
            self.assertIn('/etc/sysconfig/network-scripts/ifcfg-lo',
                          write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network-scripts/ifcfg-lo']
            expected_buf = '''
DEVICE="lo"
ONBOOT=yes
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)

            self.assertIn('/etc/sysconfig/network-scripts/ifcfg-eth0',
                          write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network-scripts/ifcfg-eth0']
            expected_buf = '''
DEVICE="eth0"
BOOTPROTO="static"
NETMASK="255.255.255.0"
IPADDR="192.168.1.5"
ONBOOT=yes
GATEWAY="192.168.1.254"
BROADCAST="192.168.1.255"
IPV6INIT=yes
IPV6ADDR="2607:f0d0:1002:0011::2/64"
IPV6_DEFAULTGW="2607:f0d0:1002:0011::1"
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)
            self.assertIn('/etc/sysconfig/network-scripts/ifcfg-eth1',
                          write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network-scripts/ifcfg-eth1']
            expected_buf = '''
DEVICE="eth1"
BOOTPROTO="static"
NETMASK="255.255.255.0"
IPADDR="192.168.1.6"
ONBOOT=no
GATEWAY="192.168.1.254"
BROADCAST="192.168.1.255"
IPV6INIT=yes
IPV6ADDR="2607:f0d0:1002:0011::3/64"
IPV6_DEFAULTGW="2607:f0d0:1002:0011::1"
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)

            self.assertIn('/etc/sysconfig/network', write_bufs)
            write_buf = write_bufs['/etc/sysconfig/network']
            expected_buf = '''
# Created by cloud-init v. 0.7
NETWORKING=yes
NETWORKING_IPV6=yes
IPV6_AUTOCONF=no
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)

    def test_simple_write_freebsd(self):
        fbsd_distro = self._get_distro('freebsd')

        write_bufs = {}
        read_bufs = {
            '/etc/rc.conf': '',
            '/etc/resolv.conf': '',
        }

        def replace_write(filename, content, mode=0o644, omode="wb"):
            buf = WriteBuffer()
            buf.mode = mode
            buf.omode = omode
            buf.write(content)
            write_bufs[filename] = buf

        def replace_read(fname, read_cb=None, quiet=False):
            if fname not in read_bufs:
                if fname in write_bufs:
                    return str(write_bufs[fname])
                raise IOError("%s not found" % fname)
            else:
                if fname in write_bufs:
                    return str(write_bufs[fname])
                return read_bufs[fname]

        with ExitStack() as mocks:
            mocks.enter_context(
                mock.patch.object(util, 'subp', return_value=('vtnet0', '')))
            mocks.enter_context(
                mock.patch.object(os.path, 'exists', return_value=False))
            mocks.enter_context(
                mock.patch.object(util, 'write_file', replace_write))
            mocks.enter_context(
                mock.patch.object(util, 'load_file', replace_read))

            fbsd_distro.apply_network(BASE_NET_CFG, False)

            self.assertIn('/etc/rc.conf', write_bufs)
            write_buf = write_bufs['/etc/rc.conf']
            expected_buf = '''
ifconfig_vtnet0="192.168.1.5 netmask 255.255.255.0"
ifconfig_vtnet1="DHCP"
defaultrouter="192.168.1.254"
'''
            self.assertCfgEquals(expected_buf, str(write_buf))
            self.assertEquals(write_buf.mode, 0o644)
