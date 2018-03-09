# grub2 Network Boot Infrastructure

Maintainer: jloeser@suse.de

## Description

This project holds all necessary configurations and script files for grub2 network boot.

## Network Boot Process

TFTP Boot root directory: `/srv/tftpboot`

### DHCP configuration

| Architecture        | Binary(s)                              |
|---------------------|----------------------------------------|
| x86_64-efi          | `grub2/bootx86.efi` > `grub2/grub.efi` |
| x86_64-legacy (pxe) | `grub2/grub.pxe`                       |
| ppc64               | `grub2/grub.ppc64`                     |
| ppc64le             | `grub2/grub.ppc64le`                   |

### Source order

| # | Configuration file                             | Comment                                                              |
|---|------------------------------------------------|----------------------------------------------------------------------|
| 1 | `grub2/grub.cfg`                               | generic root configuration                                           |
| 2 | `grub2/00-config/<mac-address>`                | autogenerated; machine specific variables                            |
|(3)| `grub2/<arch>/02-orthos-install/<hostname>`    | autogenerated, optional; sets grub2 default and timeout if triggered |
|(4)| `grub2/<arch>/01-grub.cfg`                     | optional; architecture specific variables                            |
|(5)| `grub2/<arch>/90-custom/<hostname>`            | optional; add your machine specific configuration HERE               |
| 6 | `grub2/<arch>/05-*.cfg`                        | arch specific template files for SLE, openSUSE, ...                  |

### Reset default after machine setup was triggered

Script: `grub2/scripts/setup-reset.py`

- use `rcsetup-reset start|stop`
- logfile: `/var/log/grub2/reset`

### Create machine specific stub:

Script: `grub2/scripts/setup.py`

- no manual interaction needed; triggered by Orthos
- Example:

    `grub2/scripts/setup.py --arch x86_64 \
      --mac 00:11:22:33:44:55 \
      --fqdn foobar.suse.de \
      --serial-console true \
      --serial-line 1 \
      --kernel-options-append "noresume"`
