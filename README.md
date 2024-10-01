# ODP Filing

File storage service enabling fast uploads to an ODP-integrated
Nextcloud instance, with file integrity checks.

## Development

When developing locally against a Nextcloud instance on the dev
network, use SSHFS to mount the Nextcloud upload directory to your
local machine.

### Nextcloud dev server setup

On the Nextcloud dev server, add your user to the `www-data` group:

    sudo usermod -aG www-data user

Then, add write permission for the `www-data` group to the upload
directory that you created in Nextcloud, for example:

    sudo chmod g+w /var/www/html/nextcloud/data/saeonrepo/files/Upload

### Local machine setup

On your local machine, mount the Nextcloud upload directory using SSHFS:

    sshfs \
        user@192.168.115.74:/var/www/html/nextcloud/data/saeonrepo/files/Upload \
        /home/user/mnt/devrepo_upload/

Use the following command to unmount the directory:

    fusermount -u /home/user/mnt/devrepo_upload
