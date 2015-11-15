
About swap

$ cd /etc/default/
$ sudo ln -s /opt/janitoo/src/janitoo_raspberry/utils/zram-swap.default zram-swap
$ cd /etc/init.d/
$ sudo ln -s /opt/janitoo/src/janitoo_raspberry/utils/zram-swap zram-swap
$ chmod 755 /opt/janitoo/src/janitoo_raspberry/utils/zram-swap
$ sudo update-rc.d zram-swap defaults 02 99
update-rc.d: using dependency based boot sequencing
update-rc.d: warning: default stop runlevel arguments (0 1 6) do not match zram-swap Default-Stop values (none)

Using the staff group
- add your user (pi) to it
- sudo chmod -Rf g+w /usr/local/lib/python2.7/
- sudo chmod -Rf g+w /usr/local/bin
