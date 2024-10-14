import hashlib
from os import PathLike
from pathlib import Path


class FileStoreException(Exception):
    pass


class FileStore:
    """File management for a Linux-based file system."""

    def __init__(self, base_dir: str | PathLike):
        self.base_dir = Path(base_dir)

    def put(self, data: bytes, path: str | PathLike, sha256: str) -> None:
        upload_path = self.base_dir / path

        try:
            upload_path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        except OSError as e:
            raise FileStoreException(
                f'Error creating directory at {Path(path).parent}: {e}'
            )

        try:
            with open(upload_path, 'wb') as f:
                f.write(data)
        except OSError as e:
            raise FileStoreException(
                f'Error creating file at {path}: {e}'
            )

        with open(upload_path, 'rb') as f:
            if sha256 != hashlib.sha256(f.read()).hexdigest():
                raise FileStoreException(
                    f'Error creating file at {path}: checksum verification failed'
                )

        try:
            with open(f'{upload_path}.sha256', 'wt') as f:
                f.write(f'{sha256} {upload_path.name}\n')
        except OSError as e:
            raise FileStoreException(
                f'Error creating checksum file at {path}.sha256: {e}'
            )
