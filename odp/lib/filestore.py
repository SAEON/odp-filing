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
    'relpath', 'size', 'sha256'
))


class FilestoreError(Exception):
    pass


class Filestore:
    """File storage controller.

    Incoming data are always written first to temporary directories,
    to mitigate against partial failures, filesystem errors and
    denial-of-service attacks.

    If a destination path already exists (whether a file or dir),
    an exception is raised rather than silently overwriting it.
    """

    def __init__(self, base_dir: str | PathLike):
        self.base_dir = Path(base_dir)

    def put(self, folder: str, filename: str, data: bytes, sha256: str) -> FileInfo:
        """Write file data to filename within folder relative to the base dir,
        and verify against sha256.

        Return tuple(relpath, size, sha256).
        """
        relpath = Path(folder) / filename
        destpath = self.base_dir / relpath

        if destpath.exists():
            raise FilestoreError(f'Destination path {relpath} already exists')

        with self._save_to_tmpdir(filename, data, sha256) as tmpfile:
            self._move_to_dest(tmpfile, destpath)

        return FileInfo(
            relpath, destpath.stat().st_size, sha256
        )

    def unpack(self, folder: str, filename: str, data: bytes, sha256: str) -> list[FileInfo]:
        """Unpack zipped file data into folder relative to the base dir.

        The zip file is verified against sha256 and discarded.

        Return a list of tuple(relpath, size, sha256) for all unpacked files.
        """
        with self._save_to_tmpdir(filename, data, sha256) as tmpfile:
            unpack_dir = tmpfile.parent / tmpfile.stem
            try:
                shutil.unpack_archive(tmpfile, unpack_dir / folder)
            except (OSError, ValueError) as e:
                raise FilestoreError(f'Error unpacking zip file: {e}') from e

            files = []
            errors = []
            for dirpath, dirnames, filenames in os.walk(unpack_dir):  # TODO: use Path.walk() in Python 3.12
                for filename in filenames:
                    srcpath = Path(dirpath) / filename
                    relpath = srcpath.relative_to(unpack_dir)
                    destpath = self.base_dir / relpath
                    if destpath.exists():
                        errors += [f'Destination path {relpath} already exists']
                        continue
                    with open(srcpath, 'rb') as f:
                        filehash = hashlib.sha256(f.read()).hexdigest()
                    files += [FileInfo(
                        relpath, srcpath.stat().st_size, filehash
                    )]

            if errors:
                raise FilestoreError(errors)

            for finfo in files:
                self._move_to_dest(unpack_dir / finfo.relpath, finfo.relpath)

            return files

    @contextmanager
    def _save_to_tmpdir(self, filename: str, data: bytes, sha256: str) -> ContextManager[Path]:
        """Create a temporary directory, write file data to /tmp/tmpdir/filename,
        verify against sha256, and yield the temporary file path. The temporary
        directory is deleted upon exiting the context manager."""
        with TemporaryDirectory() as tmpdir:
            try:
                with open(tmpfile := Path(tmpdir) / filename, 'wb') as f:
                    f.write(data)
            except OSError as e:
                raise FilestoreError(f'Error saving uploaded file: {e}') from e

            with open(tmpfile, 'rb') as f:
                if sha256 != hashlib.sha256(f.read()).hexdigest():
                    raise FilestoreError('Error uploading file: checksum verification failed')

            yield tmpfile

    def _move_to_dest(self, srcpath: Path, relpath: Path) -> None:
        destpath = self.base_dir / relpath
        try:
            if not destpath.parent.exists():
                destpath.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        except OSError as e:
            raise FilestoreError(f'Error creating directory at {relpath.parent}: {e}') from e

        try:
            shutil.move(srcpath, destpath)
        except OSError as e:
            raise FilestoreError(f'Error creating file at {relpath}: {e}') from e
