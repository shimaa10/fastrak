# Generic Variables

DB_NAME = 'fastrak_db'
API_ROOT = '/api/v1/fastrak'


# Generic Functions


def check_required_fields(kwargs: dict, required_fields: list):
    kwargs_keys = list(kwargs.keys())

    for field in required_fields:
        if field not in kwargs_keys:
            return False

    return True
