#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author Jan Löser <jloeser@suse.de>
# Published under the GNU Public Licence 2
import argparse
import sys
import os
import re
import logging

TFTPBOOT_DIR = '/srv/tftpboot/'
PREFIX_DIR = 'grub2/'
CONFIG_DIR = '00-config/'
DEFAULT_DIR = '02-orthos-install/'
GRUB_CFG_GLOBAL = 'grub.cfg'
GRUB_CFG_ARCH = '01-grub.cfg'
ARCHITECTURES = [
    'x86_64',
    'ppc64',
    'ppc64le',
    'aarch64'
]
FLAVOURS = [
    'install',
    'install-ssh',
    'install-auto',
    'install-auto-ssh',
    'upgrade-ssh',
    'rescue'
]
GRUB_CFG_MACHINE_FORMAT = '{0}'
STUB = """# grub2 machine stub for '{fqdn}' (autogenerated)
set arch='{architecture}'
set hostname='{hostname}'
set serial_console=false
set serial_baud=57600
set serial_line=0
set graphic_console=true
set kernel_options=""

source ${{prefix}}/${{arch}}/02-orthos-install/${{hostname}}
"""
DEFAULT_STUB = """# grub2 default for '{fqdn}' (autogenerated)
set default="{default}"
set timeout=2
"""
DEFAULT = 'local'

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='[%(asctime)s]: %(message)s')


def get_distributions(architecture=None):
    content = ''
    dist_list = ''
    grub_cfg = '{0}/{1}/{2}'.format(
        TFTPBOOT_DIR.rstrip('/'),
        PREFIX_DIR.rstrip('/'),
        GRUB_CFG_GLOBAL
    )

    try:
        with open(grub_cfg) as f:
            content = f.read()

        match = re.search(r'set dist_list=["\'](.*)["\']', content)
        if not match:
            logging.error("Couln't find '$dist_list': {0}".format(grub_cfg))
            sys.exit(1)

        for match in re.finditer(r'set dist_list=["\'](.*)["\']', content):
            dist_list = re.sub(r"\$\{dist_list\}|\$dist_list", dist_list.rstrip(), match.group(1))

    except IOError:
        logging.error("Couldn't read file: {0}".format(grub_cfg))
        sys.exit(1)

    if architecture:
        grub_cfg_architecture = '{0}/{1}/{2}/{3}'.format(
            TFTPBOOT_DIR.rstrip('/'),
            PREFIX_DIR.rstrip('/'),
            architecture,
            GRUB_CFG_ARCH
        )

        try:
            with open(grub_cfg_architecture) as f:
                content = f.read()

            for match in re.finditer(r'set dist_list=["\'](.*)["\']', content):
                dist_list = re.sub(r"\$\{dist_list\}|\$dist_list", dist_list.rstrip(), match.group(1))

        except IOError:
            pass

    return dist_list.split()

def get_distribution_flavours(architecture, default=None):
    flavours = []

    if architecture == 'generic':
        architecture = None

    distributions = get_distributions(architecture=architecture)

    for distribution in distributions:
        for flavour in FLAVOURS:
            flavours.append('{0}-{1}'.format(distribution, flavour))

    if default:
        flavours.append(DEFAULT)
    return flavours


def create_hostname_link(architecture, fqdn, mac_address):
    hostname = fqdn.split('.')[0]

    syslink_dir = '{0}/{1}/{2}/00-name-to-MAC/'.format(
        TFTPBOOT_DIR.rstrip('/'),
        PREFIX_DIR.rstrip('/'),
        architecture
    )
    syslink_filename = hostname
    syslink = syslink_dir + syslink_filename

    if os.path.islink(syslink):
        os.unlink(syslink)

    target = '{0}/.../{1}'.format(syslink_dir.rstrip('/'), mac_address)

    os.symlink(
        os.path.relpath(target, syslink_dir),
        syslink
    )


def create_stub(filename, mac_address, architecture, fqdn):
    hostname = fqdn.split('.')[0]

    with open(filename, 'w') as f:
        f.write(STUB.format(
            fqdn=fqdn,
            hostname=hostname,
            architecture=architecture
        ))

    # set ownership to 'nobody' as Orthos runs as nobody
    os.chown(filename, 65534, 65533)

    create_hostname_link(architecture, fqdn, mac_address)


def create_default(filename, default, fqdn):
    with open(filename, 'w') as f:
        f.write(DEFAULT_STUB.format(fqdn=fqdn, default=default))


def update_stub(mac_address, architecture, fqdn, **kwargs):
    buffer = ''
    hostname = fqdn.split('.')[0]

    if architecture not in ARCHITECTURES:
        logging.error("Unknown architecture: {0}".format(architecture))
        sys.exit(1)

    grub_cfg_machine = '{0}/{1}/{2}/{3}'.format(
        TFTPBOOT_DIR.rstrip('/'),
        PREFIX_DIR.rstrip('/'),
        CONFIG_DIR.rstrip('/'),
        GRUB_CFG_MACHINE_FORMAT.format(mac_address)
    )

    if not os.path.isfile(grub_cfg_machine):
        create_stub(grub_cfg_machine, mac_address, architecture, fqdn)

    update = dict([key, value] for key, value in kwargs.iteritems() if value is not None)

    if 'default' in update.keys():
        default = update.pop('default')

        for distribution in get_distributions(architecture=architecture):
            if default.startswith(distribution):
                default = '{0}>{1}'.format(distribution, default)
                break

        grub_cfg_default = '{0}/{1}/{2}/{3}/{4}'.format(
            TFTPBOOT_DIR.rstrip('/'),
            PREFIX_DIR.rstrip('/'),
            architecture,
            DEFAULT_DIR.rstrip('/'),
            hostname
        )

        logging.info("Create default file: {0} ({1})".format(grub_cfg_default, fqdn))
        create_default(grub_cfg_default, default, fqdn)

    if update:
        with open(grub_cfg_machine, 'r') as f:
            buffer = f.read()

        if re.search(r"# grub2 machine stub for '[a-zA-Z0-9\.-]+' \(autogenerated\)", buffer):
            for key, value in update.iteritems():
                buffer = re.sub(r'set {0}=[^"\'].*'.format(key), r'set {0}={1}'.format(key, value), buffer)
                buffer = re.sub(r'set {0}=".*"'.format(key), r'set {0}="{1}"'.format(key, value), buffer)
                buffer = re.sub(r"set {0}='.*'".format(key), r"set {0}='{1}'".format(key, value), buffer)

            with open(grub_cfg_machine, 'w') as f:
                f.write(buffer)
        else:
            logging.info("No changes (missing top line): {0} ({1})".format(grub_cfg_machine, fqdn))
    else:
        logging.info("No changes: {0} ({1})".format(grub_cfg_machine, fqdn))

    create_hostname_link(architecture, fqdn, mac_address)

def main():
    parser = argparse.ArgumentParser(description='Script for generating grub2 configuration stubs.')

    parser.add_argument(
        '-l',
        '--list',
        dest='list_architecture',
        metavar='ARCH',
        choices=['generic'] + ARCHITECTURES,
        help='list available distributions with flavours for architecture'
    )

    parser.add_argument(
        '--list-distributions',
        dest='list_distributions_architecture',
        metavar='ARCH',
        choices=['generic'] + ARCHITECTURES,
        help='list available distributions for architecture'
    )

    parser.add_argument(
        '--list-flavours',
        const=True,
        default=False,
        action='store_const',
        help='list available flavours'
    )

    parser.add_argument(
        '-f',
        '--fqdn',
        dest='fqdn',
        metavar='FQDN',
        help='machines FQDN'
    )

    parser.add_argument(
        '-d',
        '--default',
        dest='default',
        metavar='LABEL',
        help='set default boot label (see list)'
    )

    parser.add_argument(
        '-a',
        '--arch',
        dest='architecture',
        metavar='ARCH',
        choices=ARCHITECTURES,
        help='architecture of the machine'
    )

    parser.add_argument(
        '-m',
        '--mac',
        dest='mac_address',
        metavar='MAC',
        help='MAC address of the machine'
    )

    parser.add_argument(
        '--serial-baud',
        dest='serial_baud',
        metavar='BAUD',
        default=None,
        choices=['2400', '4800', '9600', '19200', '38400', '57600', '115200'],
        help='set baud rate (e.g. 115200)'
    )

    parser.add_argument(
        '--serial-line',
        dest='serial_line',
        metavar='LINE',
        default=None,
        help='Set serial line (e.g. 0)'
    )

    parser.add_argument(
        '--serial-console',
        dest='serial_console',
        metavar='true|false',
        default=None,
        choices=['true', 'false'],
        help='activate serial console'
    )

    parser.add_argument(
        '--graphic-console',
        dest='graphic_console',
        metavar='true|false',
        default=None,
        choices=['true', 'false'],
        help='use graphic console'
    )

    parser.add_argument(
        '--kernel-options',
        dest='kernel_options',
        metavar='KOPTS',
        default=None,
        help='machine kernel options (append kernel options line to default kernel options line with a leading \'+\'; e.g. \'+modprobe.blacklist=foo,bar splash ...\')'
    )

    parser.add_argument(
        '--timeout',
        dest='timeout',
        metavar='SECONDS',
        default=None,
        help='timeout in seconds'
    )

    options = parser.parse_args()

    if options.list_architecture:
        for record in get_distribution_flavours(options.list_architecture, default=DEFAULT):
            print(record)
        sys.exit(0)

    if options.list_distributions_architecture:
        for record in get_distributions(options.list_distributions_architecture):
            print(record)
        sys.exit(0)

    if options.list_flavours:
        for record in FLAVOURS:
            print(record)
        sys.exit(0)

    if not options.mac_address:
        logging.error("MAC address required!")
        sys.exit(1)

    if not options.architecture:
        logging.error("Architecture required!")
        sys.exit(1)

    if not options.fqdn:
        logging.error("FQDN required!")
        sys.exit(1)

    update_stub(
        options.mac_address.lower(),
        options.architecture,
        options.fqdn.lower(),
        default=options.default,
        serial_console=options.serial_console,
        serial_baud=options.serial_baud,
        serial_line=options.serial_line,
        graphic_console=options.graphic_console,
        kernel_options=options.kernel_options,
        timeout=options.timeout
    )
    sys.exit(0)

if __name__ == '__main__':
    main()
