from flask import Blueprint, g
from utils.config import Config

language_str = ', '.join(Config.LANGUAGES)
default_lang = Config.BABEL_DEFAULT_LOCALE

inter_bp = Blueprint('inter', __name__, url_prefix=f'/<any({language_str}):lang>')

@inter_bp.url_value_preprocessor
def pull_lang(endpoint, values):
    lang = values.pop('lang')
    if lang and lang in Config.LANGUAGES:
        g.lang = lang
    else:
        g.lang = default_lang

@inter_bp.url_defaults
def add_language_code(endpoint, values):
    values.setdefault('lang', g.get('lang', default_lang))