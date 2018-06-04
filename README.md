# grub2 Network Boot Infrastructure

Maintainer: jloeser@suse.de

## Description

This project holds all necessary configurations and script files for grub2 network boot.

## Network Boot Process

TFTP Boot root directory: `/srv/tftpboot`

### DHCP configuration

| Architecture        | Binary(s)                               |
|---------------------|-----------------------------------------|
| x86_64-efi          | `grub2/shim-x86.efi` > `grub2/grub.efi` |
| x86_64-legacy (pxe) | `pxelinux.0` > `grub2/grub.0`           |
| ppc64               | `grub2/grub.ppc64`                      |
| ppc64le             | `grub2/grub.ppc64le`                    |

EFI uses currently `shim-x86.efi` to bootstrap the grub2 EFI binary.

On `x86_64-legacy` there is an grub2/grub1 issue! When booting the `grub.pxe` (grub2) via network,
using `local` for chainloading grub1 from disk, the kernel/initrd gets loaded but does not start.
Therefor, we load `pxelinux.0` on non-EFI (=legacy) x86_64 machines and bootstrap grub2 in case of
an Orthos setup/installation (label: `network`). Otherwise, the `pxelinux.0` just boots from disk
as usual (label: `local`).

### Source order

| # | Configuration file                             | Comment                                                              |
|---|------------------------------------------------|----------------------------------------------------------------------|
| 1 | `grub2/grub.cfg`                               | generic root configuration                                           |
| 2 | `grub2/00-config/<mac-address>`                | autogenerated; machine specific variables                            |
|(3)| `grub2/<arch>/01-orthos-install/<hostname>`    | autogenerated, optional; sets grub2 default and timeout if triggered |
|(4)| `grub2/<arch>/02-grub.cfg`                     | optional; architecture specific variables                            |
|(5)| `grub2/<arch>/90-custom/<hostname>`            | optional; add your machine specific configuration HERE               |
| 6 | `grub2/<arch>/99-*.cfg`                        | arch specific template files for SLE, openSUSE, ...                  |

### Reset default after machine setup was triggered

Script: `grub2/scripts/setup-reset.py`

- use `rcsetup-reset start|stop`
- logfile: `/var/log/grub2/reset`
- required: `/var/log/tftpd.log` (see below)

### Create machine specific stub:

Script: `grub2/scripts/setup.py`

- no manual interaction needed; triggered by Orthos
- Example:

    `grub2/scripts/setup.py --arch x86_64 \
      --mac 00:11:22:33:44:55 \
      --fqdn foobar.suse.de \
      --serial-console true \
      --serial-line 1 \
      --kernel-options "+noresume"`

### Remove machine specific grub2 default files (clean up for unclaimed files):

Script: `grub2/scripts/setup-remove-deprecated-defaults.py`

- remove files (3) if mtime is older than 4h
- cron job: `/etc/cron.d/remove_deprecated_defaults` (every hour)
- Example:

    `grub2/scripts/setup-remove-deprecated-defaults.py`

### Create tftpd.log file

- install TFTP server: `zypper in tftp`
- create empty log file: `touch /var/log/tftpd.log`
- change file permissions: `chmod 644 /var/log/tftpd.log`
- modify `/etc/xinetd.d/tftp`:

```
# default: off
# description: tftp service is provided primarily for booting or when a \
#       router need an upgrade. Most sites run this only on machines acting as
#       "boot servers".
service tftp
{
    disable         = no
    socket_type     = dgram
    protocol        = udp
    wait            = yes
    user            = root
    server          = /usr/sbin/in.tftpd
    server_args     =  -v -v -s /tftpboot
    flags           = IPv6 IPv4
}
```

- restart xinetd service: `rcxinetd restart`
- restart tftpd service: `rctftp restart`
- modify `/etc/systemd/journald.conf` (remove comments):

```
...
ForwardToSyslog=yes
MaxLevelSyslog=debug
...
```
- add rsyslog rule in `/etc/rsyslog.conf`:

```
...
# tftpd log
#
if      ($programname == 'in.tftpd') or \
        ($msg contains 'tftpd') \
then {
        -/var/log/tftpd.log
}
...
```