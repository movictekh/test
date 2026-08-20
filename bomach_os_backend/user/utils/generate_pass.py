import secrets
import string


def generate_password(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits

    password = "".join(secrets.choice(alphabet) for _ in range(length))

    return password
