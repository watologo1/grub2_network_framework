#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author Jan Löser <jloeser@suse.de>
# Published under the GNU Public Licence 2
import subprocess
import argparse
import os
import sys


ORTHOS_CMD = '/mounts/users-space/archteam/bin/orthos'
ORTHOS_QUERY = "query name, sconsole, serial_baud, serial_kernel_device, ifmac where domain = {0} and ifname != '-'"
DOMAIN_ID_ARCHITECTURE = {
    'x86_64': (1, 'x86_64'),
    'ppc': (2, 'ppc64'),
    #'ia64': (5, 'ia64'),
    #'arm': (6, 'aarch64'),
    #'s390x': (7, 's390x'),
    'nts': (10, 'x86_64'),
    #'prague': (12, 'x86_64'),
    'ppc64le': (13, 'ppc64le'),
    #'provo': (14, 'x86_64'),
    #'qa': (15, 'x86_64'),
    #'hp_partner_lab': (16, 'x86_64'),
    #'prague_qa': (17, 'x86_64'),
    'storage': (18, 'x86_64'),
    #'desktop': (19, 'x86_64'),
}


def get_list(domain):
    try:
        cmd = ORTHOS_QUERY.format(DOMAIN_ID_ARCHITECTURE[domain][0])
    except:
        print("Unknown domain!")
        sys.exit(1)

    process = subprocess.Popen(
        'echo "{0}" | {1}'.format(cmd, ORTHOS_CMD),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    data = process.communicate()

    stdout, stderr, exitcode = data[0].decode('utf-8'), data[1].decode('utf-8'), process.returncode

    if exitcode != 0:
        print("Failed: {0}".format(cmd))
        sys.exit(1)

    data = []
    for record in stdout.split('\n')[1:-3]:
        data.append(tuple(record.split()))

    return data


def create_stubs(domain, delete=False):
    data = get_list(domain)

    for machine in data:
        architecture = DOMAIN_ID_ARCHITECTURE[domain][1]

        serial_console = ''
        serial_baud = ''
        serial_line = ''

        orthos_name = machine[0]
        orthos_sconsole = machine[1]
        orthos_serial_baud = machine[2]
        orthos_serial_kernel_device = machine[3]
        orthos_ifmac = machine[4]

        fqdn = orthos_name
        mac_address = orthos_ifmac

        if orthos_sconsole == 'True':
            serial_console = '--serial-console true '
            serial_line = '--serial-line {0} '.format(orthos_serial_kernel_device)

        if orthos_serial_baud in ['2400', '4800', '9600', '19200', '38400', '57600', '115200']:
            serial_baud = '--serial-baud {0} '.format(orthos_serial_baud)

        cmd = 'sudo /srv/tftpboot/grub2/scripts/setup.py -a {0} -f {1} -m {2} '.format(
            architecture,
            fqdn,
            mac_address
        )
        cmd = cmd + serial_console + serial_line + serial_baud

        if delete:
            grub_cfg_machine = '/srv/tftpboot/grub2/00-config/{0}'.format(mac_address.lower())
            if os.path.isfile(grub_cfg_machine):
                os.remove(grub_cfg_machine)

        os.system(cmd)

def main():
    parser = argparse.ArgumentParser(description='Script for intial generating grub2 configuration stubs from Orthos domains')

    parser.add_argument(
        '-l',
        action='store_true',
        help='list available Orthos domains'
    )

    parser.add_argument(
        '-D',
        action='store_true',
        help='Delete existing stubs'
    )

    parser.add_argument(
        'domain',
        metavar='DOMAIN',
        nargs='?',
        help='Orthos domain'
    )

    options = parser.parse_args()

    if options.l:
        for domain in DOMAIN_ID_ARCHITECTURE.keys():
            print(domain)
        sys.exit(0)

    if options.domain:
        create_stubs(options.domain, delete=options.D)


if __name__ == '__main__':
    main()
