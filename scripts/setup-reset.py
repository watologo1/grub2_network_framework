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
from threading import Lock

mutex_access_reset_list = Lock()

TFTP_LOG = '/var/log/tftpd.log'
LOG_FILE = '/var/log/grub2/reset'
TFTPBOOT_DIR = '/srv/tftpboot/'
PREFIX_DIR = 'grub2/'
DEFAULT_DIR = '01-orthos-install/'
GRUB_CFG_MACHINE_FORMAT = '{0}'
PXE_PREFIX_DIR = 'pxelinux.cfg/'

reset_list = []
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format='[%(asctime)s]: %(message)s')

logging.info('Start listening...')


def get_fqdn(ipv4):
    try:
        return socket.getfqdn(ipv4)
    except Exception:
        logging.error("IPv4 unresolvable: {0}".format(ipv4))
    return None


def reset_pxe(fqdn, architecture):
    hostname = fqdn.split('.')[0]

    pxe_cfg_symlink = '{0}/{1}/{2}/00-name-to-MAC/{3}'.format(
        TFTPBOOT_DIR.rstrip('/'),
        PXE_PREFIX_DIR.rstrip('/'),
        architecture,
        hostname
    )

    if os.path.islink(pxe_cfg_symlink):
        pxe_cfg_machine = os.path.realpath(pxe_cfg_symlink)

        with open(pxe_cfg_machine, 'r') as f:
            buffer = f.read()

        if re.search(r"# pxe bootstrap stub for '[a-zA-Z0-9\.-]+' \(autogenerated\)", buffer):
            buffer = re.sub(r'default[ \t]+.*', r'default local', buffer)

            logging.info("PXE default changed to 'local': {0} ({1})".format(pxe_cfg_machine, fqdn))

            with open(pxe_cfg_machine, 'w') as f:
                f.write(buffer)
        else:
            logging.info("No changes (missing top line): {0} ({1})".format(pxe_cfg_machine, fqdn))
    else:
        logging.debug("No PXE configuration symlink found: {0}".format(pxe_cfg_symlink))


def reset(fqdn, ipv4, filename, architecture):
    logging.debug("Start thread ({0} {1} {2} {3})...".format(fqdn, ipv4, filename, architecture))

    mutex_access_reset_list.acquire()
    if filename in reset_list:
        logging.debug("Exit thread (filename already handled by another thread)")
        mutex_access_reset_list.release()
        return
    mutex_access_reset_list.release()

    mutex_access_reset_list.acquire()
    reset_list.append(filename)
    mutex_access_reset_list.release()

    time.sleep(10)

    grub_cfg_default = '{0}/{1}/{2}/{3}/{4}'.format(
        TFTPBOOT_DIR.rstrip('/'),
        PREFIX_DIR.rstrip('/'),
        architecture,
        DEFAULT_DIR.rstrip('/'),
        filename
    )

    if os.path.isfile(grub_cfg_default):
        logging.info("Remove default: {0}".format(grub_cfg_default))
        os.remove(grub_cfg_default)
    else:
        logging.warning("File doesn't exist: {0}".format(grub_cfg_default))

    if architecture in ['x86_64']:
        reset_pxe(fqdn, architecture)

    mutex_access_reset_list.acquire()
    reset_list.remove(filename)
    mutex_access_reset_list.release()


    logging.debug('Exit thread')


def follow(f):
    f.seek(0,2)
    start = ''
    while True:
        line = f.readline()
        if not line:
            time.sleep(0.5)
            continue
        if line[-1] != '\n':
            logging.warning("Incomplete line: '{0}'".format(line))
            start = start + line
            continue
        elif '\n' in line and line[-1] != '\n':
            logger.exception("Interspersed new-line: '{0}'".format(line))
            sys.exit(1)
        if start:
            line = start + line
            start = ''

        yield line.strip('\n')


if __name__ == '__main__':
    logfile = open(TFTP_LOG, 'r')
    lines = follow(logfile)
    for line in lines:
        pattern1 = r'.*from (\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}) filename '
        pattern2 = r'/?{0}/(\w+)/{1}/'.format(PREFIX_DIR.rstrip('/'), DEFAULT_DIR.rstrip('/'))
        pattern3 = r'([a-zA-Z0-9-\.]+)'

        match = re.search(pattern1 + pattern2 + pattern3, line)

        if match:
            ipv4 = match.group(1)
            fqdn = get_fqdn(ipv4)
            architecture = match.group(2)
            filename = match.group(3)

            if fqdn is None:
                logging.warning("No FQDN found for {0}".format(ipv4))
                continue

            if fqdn.split('.')[0] != filename:
                logging.warning("Mismatch: {0} (fqdn) <-> {1} (requested filename)".format(fqdn, filename))

            thread.start_new_thread(reset, (fqdn, ipv4, filename, architecture))
