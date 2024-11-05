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
    if (val := request.args.get(arg)) is None and default is None:
        raise SanicException(f"Expecting arg '{arg}'", status_code=400)
    return val


def _get_filestore(request: Request) -> Filestore:
    return Filestore(request.app.config.ODP_UPLOAD_DIR)


@bp.put('/<folder:path>')
async def upload_file(request: Request, folder: str) -> HTTPResponse:
    """Upload a file to `folder`, relative to the filestore base directory.

    If unpack is true, the file is unzipped into `folder`.

    The response is a JSON object whose keys are file paths relative
    to the filestore's base directory, for every file that has been
    created/updated. The corresponding values are length 2 arrays
    of [file size, file hash].
    """
    file = _get_file(request, 'file')
    filename = _get_arg(request, 'filename')
    sha256 = _get_arg(request, 'sha256')
    unpack = _get_arg(request, 'unpack', False)
    filestore = _get_filestore(request)

    if '..' in folder:
        raise SanicException("'..' not allowed in folder", status_code=422)

    if Path(folder).is_absolute():
        raise SanicException('folder must be relative', status_code=422)

    if not (filename := secure_filename(filename)):
        raise SanicException('invalid filename', status_code=422)

    if unpack:
        filename = filename.lower()
        if Path(filename).suffix != '.zip':
            raise SanicException('unpack is supported only for zip files', status_code=422)

    try:
        if unpack:
            result = {
                finfo.relpath: [finfo.size, finfo.sha256]
                for finfo in filestore.unpack(folder, filename, file.body, sha256)
            }
        else:
            finfo = filestore.put(folder, filename, file.body, sha256)
            result = {
                finfo.relpath: [finfo.size, finfo.sha256]
            }

    except FilestoreError as e:
        raise SanicException(str(e), status_code=422) from e

    return json(result)
