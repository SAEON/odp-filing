import shutil

from sanic import Blueprint, HTTPResponse, json, Request, SanicException

from odp.lib import get_filestore, get_request_arg, get_request_file, validate_path
from odp.lib.filestore import FilestoreError

bp = Blueprint('upload', url_prefix='/upload')


@bp.before_server_start
async def register_unpack_formats(*_):
    """Ensure only zip is registered. The tar formats come
    with security considerations that are complex to address."""
    unpack_formats = shutil.get_unpack_formats()
    for fmt, _, _ in unpack_formats:
        if fmt != 'zip':
            shutil.unregister_unpack_format(fmt)


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
    path = validate_path(path)
    file = get_request_file(request, 'file')
    sha256 = get_request_arg(request, 'sha256')
    unpack = get_request_arg(request, 'unpack', False)
    filestore = get_filestore(request)

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
    path = validate_path(path)
    filestore = get_filestore(request)

    try:
        filestore.delete(path)
    except FilestoreError as e:
        raise SanicException(e.error_detail, e.status_code) from e

    return json(None)
