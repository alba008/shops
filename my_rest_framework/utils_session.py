# my_rest_framework/utils_session.py
from decimal import Decimal

def _jsonify(x):
    if isinstance(x, Decimal): return str(x)
    if isinstance(x, dict):    return {k: _jsonify(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return type(x)(_jsonify(v) for v in x)
    return x

def sanitize_session(session):
    changed = False
    for k in list(session.keys()):
        v = session[k]
        j = _jsonify(v)
        if j is not v:
            session[k] = j
            changed = True
    if changed:
        session.modified = True
