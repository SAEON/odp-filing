from sanic import Blueprint, file, HTTPResponse, Request

from odp.lib import get_filestore, validate_path

bp = Blueprint('download', url_prefix='/download')


@bp.get('/<path:path>')
async def download_file(request: Request, path: str) -> HTTPResponse:
    path = validate_path(path)
    filestore = get_filestore(request)
    return await file(filestore.base_dir / path)
