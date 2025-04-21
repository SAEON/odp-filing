import hashlib
import os
import shutil
from collections import namedtuple
from contextlib import contextmanager
from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ContextManager

FileInfo = namedtuple('FileInfo', (
    'path', 'size', 'sha256'
))


class FilestoreError(Exception):
    def __init__(self, status_code: int, error_detail: str):
        self.status_code = status_code
        self.error_detail = error_detail


class Filestore:
    """File storage controller.

    Incoming data are always written first to temporary directories,
    to mitigate against partial failures, filesystem errors and
    denial-of-service attacks.
    """

    def __init__(self, base_dir: str | PathLike):
        self.base_dir = Path(base_dir)

    def put(self, path: Path, data: bytes, sha256: str) -> FileInfo:
        """Write data to a file at path, relative to the base dir,
        and verify against sha256.

        Return tuple(path, size, sha256).
        """
        with self._save_to_tmpdir(path.name, data, sha256) as tmpfile:
            self._move_to_dest(tmpfile, path)

        size = (self.base_dir / path).stat().st_size
        return FileInfo(
            path, size, sha256
        )

    def unpack(self, path: Path, data: bytes, sha256: str) -> list[FileInfo]:
        """Unpack zipped data into the parent directory of path, relative
        to the base dir.

        The uploaded zip file is verified against sha256 and discarded.

        Return a list of tuple(path, size, sha256) for all unpacked files.
        """
        with self._save_to_tmpdir(path.name, data, sha256) as tmpfile:
            unpack_dir = tmpfile.parent / tmpfile.stem
            try:
                shutil.unpack_archive(tmpfile, unpack_dir / path.parent)
            except (OSError, ValueError) as e:
                raise FilestoreError(422, f'Error unpacking zip file: {e}') from e

            files = []
            for dirpath, dirnames, filenames in os.walk(unpack_dir):  # TODO: use Path.walk() in Python 3.12
                for filename in filenames:
                    srcpath = Path(dirpath) / filename
                    relpath = srcpath.relative_to(unpack_dir)
                    with open(srcpath, 'rb') as f:
                        filehash = hashlib.sha256(f.read()).hexdigest()
                    files += [FileInfo(
                        relpath, srcpath.stat().st_size, filehash
                    )]

            for finfo in files:
                self._move_to_dest(unpack_dir / finfo.path, finfo.path)

            return files

    def delete(self, path: Path) -> None:
        abspath = self.base_dir / path
        try:
            os.remove(abspath)
        except FileNotFoundError as e:
            raise FilestoreError(404, f'{path} not found') from e
        except OSError as e:
            raise FilestoreError(422, f'Error deleting file at {path}: {e}') from e

    @contextmanager
    def _save_to_tmpdir(self, filename: str, data: bytes, sha256: str) -> ContextManager[Path]:
        """Create a temporary directory, write file data to /tmp/tmpdir/filename,
        verify against sha256, and yield the temporary file path. The temporary
        directory is deleted upon exiting the context manager."""
        with TemporaryDirectory() as tmpdir:
            try:
                # ensure lowercase suffix for zip files
                with open(tmpfile := Path(tmpdir) / filename.lower(), 'wb') as f:
                    f.write(data)
            except OSError as e:
                raise FilestoreError(422, f'Error saving uploaded file: {e}') from e

            with open(tmpfile, 'rb') as f:
                if sha256 != hashlib.sha256(f.read()).hexdigest():
                    raise FilestoreError(422, 'Error uploading file: checksum verification failed')

            yield tmpfile

    def _move_to_dest(self, srcpath: Path, path: Path) -> None:
        """Move file at srcpath (absolute) to path relative to the base dir."""
        destpath = self.base_dir / path
        try:
            if not destpath.parent.exists():
                destpath.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        except OSError as e:
            raise FilestoreError(422, f'Error creating directory at {path.parent}: {e}') from e

        try:
            shutil.move(srcpath, destpath)
        except OSError as e:
            raise FilestoreError(422, f'Error creating file at {path}: {e}') from e
