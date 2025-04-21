import shutil
from pathlib import Path

from sanic import Blueprint, HTTPResponse, json, Request, SanicException
from sanic.request import File
from werkzeug.utils import secure_filename

from odp.lib.filestore import Filestore, FilestoreError

bp = Blueprint('upload', url_prefix='/upload')


@bp.before_server_start
async def register_unpack_formats(*_):
    """Ensure only zip is registered. The tar formats come
    with security considerations that are complex to address."""
    unpack_formats = shutil.get_unpack_formats()
    for fmt, _, _ in unpack_formats:
        if fmt != 'zip':
            shutil.unregister_unpack_format(fmt)


def _get_file(request: Request, arg: str) -> File:
    if not (file := request.files.get(arg)):
        raise SanicException(f"Expecting upload '{arg}'", status_code=400)
    return file


def _get_arg(request: Request, arg: str, default=None) -> str:
    if (val := request.args.get(arg)) is None:
        if (val := default) is None:
            raise SanicException(f"Expecting arg '{arg}'", status_code=400)
    return val


def _get_filestore(request: Request) -> Filestore:
    return Filestore(request.app.config.ODP_UPLOAD_DIR)


def _validate_path(path: str) -> Path:
    path = Path(path)
    if path.is_absolute():
        raise SanicException('path must be relative', status_code=400)

    for part in path.parts:
        if part != secure_filename(part):
            raise SanicException('invalid path', status_code=400)

    return path


@bp.put('/<path:path>')
async def upload_file(request: Request, path: str) -> HTTPResponse:
    """Upload a file to `path`, relative to the filestore base directory.

    If unpack is true, the file is unzipped at the parent of `path`.

    Existing files are replaced.

    The response is a JSON object whose keys are file paths relative
    to the filestore base directory, for every file that has been
    created/updated. The corresponding values are length 2 arrays
    of [file size, file hash].
    """
    path = _validate_path(path)
    file = _get_file(request, 'file')
    sha256 = _get_arg(request, 'sha256')
    unpack = _get_arg(request, 'unpack', False)
    filestore = _get_filestore(request)

    if unpack and path.suffix.lower() != '.zip':
        raise SanicException('unpack is supported only for zip files', status_code=400)

    try:
        if unpack:
            result = {
                finfo.path: [finfo.size, finfo.sha256]
                for finfo in filestore.unpack(path, file.body, sha256)
            }
        else:
            finfo = filestore.put(path, file.body, sha256)
            result = {
                finfo.path: [finfo.size, finfo.sha256]
            }

    except FilestoreError as e:
        raise SanicException(e.error_detail, e.status_code) from e

    return json(result)


@bp.delete('/<path:path>')
async def delete_file(request: Request, path: str) -> HTTPResponse:
    """Delete the file at `path`, relative to the filestore base directory."""
    path = _validate_path(path)
    filestore = _get_filestore(request)

    try:
        filestore.delete(path)
    except FilestoreError as e:
        raise SanicException(e.error_detail, e.status_code) from e

    return json(None)
