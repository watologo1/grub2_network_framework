#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author Jan Löser <jloeser@suse.de>
# Published under the GNU Public Licence 2
import sys
import os
import time
import logging
from datetime import datetime
from datetime import timedelta

LOG_FILE = '/var/log/grub2/remove-deprecated-defaults'
TFTPBOOT_DIR = '/srv/tftpboot/'
PREFIX_DIR = 'grub2/'
DEFAULT_DIR = '01-orthos-install/'
ARCHITECTURES = [
    'x86_64',
    'ppc64',
    'ppc64le',
    'aarch64'
]
TIMEDELTA_HOURS = 4

logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format='[%(asctime)s]: %(message)s')


if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from setup_reset import reset_pxe

    logging.debug("Start...")

    for architecture in ARCHITECTURES:
        directory = '{0}/{1}/{2}/{3}'.format(
            TFTPBOOT_DIR.rstrip('/'),
            PREFIX_DIR.rstrip('/'),
            architecture,
            DEFAULT_DIR.rstrip('/')
        )
        if not os.path.isdir(directory):
            logging.debug("Does't exist: {0}".format(directory))
            continue

        filenames = os.listdir(directory)

        for filename in filenames:
            file = '{0}/{1}'.format(directory.rstrip('/'), filename)

            modified_ts = os.path.getmtime(file)
            modified = datetime.fromtimestamp(modified_ts)

            created_ts = os.path.getctime(file)
            created = datetime.fromtimestamp(created_ts)

            if modified != created:
                logging.warning("File was modified: {0}".format(file))

            timedelta_ = timedelta(hours=TIMEDELTA_HOURS)

            if datetime.now() - modified > timedelta_:
                logging.info('Delete deprecated default file: {0}'.format(file))
                os.remove(file)

                if architecture == 'x86_64':
                    logging.debug('Try to reset PXE configuration for: {0}'.format(filename))
                    reset_pxe(filename, architecture)

    logging.debug("Exit.")
