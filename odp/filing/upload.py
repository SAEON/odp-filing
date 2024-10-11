import hashlib
from pathlib import Path

from sanic import Blueprint, HTTPResponse, Request, SanicException, text

from odp.lib.nextcloud import NextcloudOCC

bp = Blueprint('upload', url_prefix='/upload')


@bp.post('/<path:path>')
async def upload_file(request: Request, path: str) -> HTTPResponse:
    data_dir = Path(request.app.config.ODP_DATA_DIR)
    nc_user = request.app.config.ODP_NC_USER
    upload_folder = Path(request.app.config.ODP_UPLOAD_FOLDER)
    files_relative_path = upload_folder / path
    upload_path = data_dir / nc_user / 'files' / files_relative_path

    occ_path = request.app.config.ODP_OCC_PATH
    php_path = request.app.config.ODP_PHP_PATH
    occ = NextcloudOCC(occ_path, php_path, nc_user)

    if not (file := request.files.get('file')):
        raise SanicException("Expecting upload 'file'", status_code=400)

    if not (sha256 := request.args.get('sha256')):
        raise SanicException("Expecting arg 'sha256'", status_code=400)

    try:
        upload_path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError as e:
        raise SanicException(
            f'Error creating directory at {Path(path).parent}: {e}', status_code=422
        )

    try:
        with open(upload_path, 'wb') as f:
            f.write(file.body)
    except OSError as e:
        raise SanicException(
            f'Error creating file at {path}: {e}', status_code=422
        )

    with open(upload_path, 'rb') as f:
        if sha256 != hashlib.sha256(f.read()).hexdigest():
            raise SanicException(
                f'Error creating file at {path}: checksum verification failed', status_code=422
            )

    occ.rescan_path(files_relative_path)

    return text('File uploaded', status=201)
