import subprocess
from os import PathLike


class NextcloudOCC:
    """Encapsulates Nextcloud's `occ` command.

    https://docs.nextcloud.com/server/latest/admin_manual/occ_command.html
    """

    def __init__(
            self,
            occ_path: str,
            php_path: str,
            nc_user: str,
    ):
        self.occ_path = occ_path
        self.php_path = php_path
        self.nc_user = nc_user

    def _execute(
            self,
            command: str,
            options: list[str],
            arguments: list[str],
    ):
        try:
            result = subprocess.run(
                [self.php_path, self.occ_path, command] + options + arguments,
            )
            result.check_returncode()
        except Exception as e:
            print(e)
            raise

    def rescan_path(self, relative_path: str | PathLike):
        """Rescan the given file/folder path, which is relative to
        the Nextcloud user's files root."""
        self._execute(
            'files:scan',
            [f'--path=/{self.nc_user}/files/{relative_path}'],
            [],
        )
