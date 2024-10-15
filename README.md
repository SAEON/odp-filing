# ODP Filing

File storage service enabling fast uploads to a file server,
with file integrity checks.

## Nextcloud integration

### Development

Use PyCharm Remote Development to run/debug this service alongside
a Nextcloud instance on a dev server. You will need to connect as
the HTTP user (`www-data` on Debian/Ubuntu) to permit writing files
to the Nextcloud data directory.

This requires a bit of preliminary setup on the server (as root)...

Stop Apache and kill any lingering `www-data` processes:

    systemctl stop apache2
    pkill -u www-data

Set a password for `www-data`:

    passwd www-data

Enable logins and set up home dir for `www-data`:

    usermod -d /home/www-data -s /bin/bash www-data
    mkdir /home/www-data
    chown www-data:www-data /home/www-data

Restart Apache:

    systemctl start apache2

### Deployment

Create a cron job to synchronize the Nextcloud DB with the
file system.

Edit the crontab for the HTTP user:

    sudo crontab -e -u www-data

For example, to rescan all files under the `Upload` folder of
the Nextcloud user `saeonrepo`, every 10 minutes:

    */10 * * * * /usr/bin/php /var/www/html/nextcloud/occ files:scan --quiet --path=/saeonrepo/files/Upload
