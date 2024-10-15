from sanic import Blueprint, HTTPResponse, Request, SanicException, text

from odp.lib.filestore import Filestore, FilestoreError

bp = Blueprint('upload', url_prefix='/upload')


@bp.post('/<path:path>')
async def upload_file(request: Request, path: str) -> HTTPResponse:
    if not (file := request.files.get('file')):
        raise SanicException("Expecting upload 'file'", status_code=400)

    if not (sha256 := request.args.get('sha256')):
        raise SanicException("Expecting arg 'sha256'", status_code=400)

    filestore = Filestore(request.app.config.ODP_UPLOAD_DIR)
    try:
        filestore.put(file.body, path, sha256)
    except FilestoreError as e:
        raise SanicException(str(e), status_code=422) from e

    return text('File uploaded', status=201)
