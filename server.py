from dotenv import dotenv_values
from sanic import Sanic

from odp.filing import upload


def create_app():
    app = Sanic('odp-filing', env_prefix='ODP_')
    app.config.update(dotenv_values('.env'))
    app.blueprint(upload.bp)
    return app
