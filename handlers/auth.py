import json
import os
from config import OWNER_ID

USERS_FILE = os.path.join(os.path.dirname(__file__), '..', 'allowed_users.json')


def _load_users() -> list:
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def _save_users(users: list):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def is_authorized(user_id: int) -> bool:
    if is_owner(user_id):
        return True
    return user_id in _load_users()


def add_user(user_id: int):
    users = _load_users()
    if user_id not in users:
        users.append(user_id)
        _save_users(users)


def remove_user(user_id: int):
    users = _load_users()
    if user_id in users:
        users.remove(user_id)
        _save_users(users)


def get_allowed_users() -> list:
    return _load_users()
