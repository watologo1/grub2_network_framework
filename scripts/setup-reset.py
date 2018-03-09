#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author Jan Löser <jloeser@suse.de>
# Published under the GNU Public Licence 2
import sys
import os
import re
import time
import socket
import thread
import logging

TFTP_LOG = '/var/log/tftpd.log'
LOG_FILE = '/var/log/grub2/reset'
TFTPBOOT_DIR = '/srv/tftpboot/'
PREFIX_DIR = 'grub2/'
DEFAULT_DIR = '02-orthos-install/'
GRUB_CFG_MACHINE_FORMAT = '{0}'

reset_list = []
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='[%(asctime)s]: %(message)s')

logging.info('Start listening...')

def get_fqdn(ipv4):
    try:
        return socket.getfqdn(ipv4)
    except Exception:
        logging.error("IPv4 unresolvable: {0}".format(ipv4))
        return None

def reset(fqdn, ipv4, filename, architecture):
    if filename in reset_list:
        return

    hostname = fqdn.split('.')[0]
    reset_list.append(filename)

    time.sleep(10)

    grub_cfg_default = '{0}/{1}/{2}/{3}/{4}'.format(
        TFTPBOOT_DIR.rstrip('/'),
        PREFIX_DIR.rstrip('/'),
        architecture,
        DEFAULT_DIR.rstrip('/'),
        hostname
    )

    if os.path.isfile(grub_cfg_default):
        logging.info("Remove default: {0}".format(grub_cfg_default))
        os.remove(grub_cfg_default)

    reset_list.remove(filename)


# https://stackoverflow.com/questions/5419888/reading-from-a-frequently-updated-file
def follow(f):
    f.seek(0,2)
    while True:
        line = f.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line.strip('\n')

if __name__ == '__main__':
    logfile = open(TFTP_LOG, 'r')
    lines = follow(logfile)
    for line in lines:
        pattern1 = r'.*from (\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}) filename '
        pattern2 = r'{0}/(\w+)/{1}/'.format(PREFIX_DIR.rstrip('/'), DEFAULT_DIR.rstrip('/'))
        pattern3 = r'([a-zA-Z0-9-\.]+)'

        match = re.search(pattern1 + pattern2 + pattern3, line)

        if match:
            ipv4 = match.group(1)
            fqdn = get_fqdn(ipv4)
            architecture = match.group(2)
            filename = match.group(3)

            thread.start_new_thread(reset, (fqdn, ipv4, filename, architecture))
