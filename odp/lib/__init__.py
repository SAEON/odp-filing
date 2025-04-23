from pathlib import Path

from sanic import Request, SanicException
from sanic.request import File
from werkzeug.utils import secure_filename

from odp.lib.filestore import Filestore


def get_request_arg(request: Request, arg: str, default=None) -> str:
    if (val := request.args.get(arg)) is None:
        if (val := default) is None:
            raise SanicException(f"Expecting arg '{arg}'", status_code=400)
    return val


def get_request_file(request: Request, arg: str) -> File:
    if not (file := request.files.get(arg)):
        raise SanicException(f"Expecting upload '{arg}'", status_code=400)
    return file


def get_filestore(request: Request) -> Filestore:
    return Filestore(request.app.config.ODP_UPLOAD_DIR)


def validate_path(path: str) -> Path:
    path = Path(path)
    if path.is_absolute():
        raise SanicException('path must be relative', status_code=400)

    for part in path.parts:
        if part != secure_filename(part):
            raise SanicException('invalid path', status_code=400)

    return path
