from pathlib import Path

from sanic import Blueprint, HTTPResponse, Request, SanicException, text

from odp.lib.filestore import FileStore, FileStoreException
from odp.lib.nextcloud import NextcloudOCC

bp = Blueprint('upload', url_prefix='/upload')


@bp.post('/<path:path>')
async def upload_file(request: Request, path: str) -> HTTPResponse:
    data_dir = Path(request.app.config.ODP_DATA_DIR)
    nc_user = request.app.config.ODP_NC_USER
    upload_folder = request.app.config.ODP_UPLOAD_FOLDER
    occ_path = request.app.config.ODP_OCC_PATH
    php_path = request.app.config.ODP_PHP_PATH

    if not (file := request.files.get('file')):
        raise SanicException("Expecting upload 'file'", status_code=400)

    if not (sha256 := request.args.get('sha256')):
        raise SanicException("Expecting arg 'sha256'", status_code=400)

    file_store = FileStore(data_dir / nc_user / 'files' / upload_folder)
    try:
        file_store.put(file.body, path, sha256)
    except FileStoreException as e:
        raise SanicException(str(e), status_code=422) from e

    occ = NextcloudOCC(occ_path, php_path, nc_user, upload_folder)
    occ.rescan_path(Path(path).parent)

    return text('File uploaded', status=201)
