import hashlib
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from server.managers.accounts import AccountManager

SALT = b'gawr gura for president'

INT_SIZE = 4
MAX_USERNAME_SIZE = 420
MAX_PASSWORD_SIZE = 420


def handle_login(raw_data: bytes, client, accounts: 'AccountManager'):
    attempt = LoginAttempt.from_network_message(raw_data)
    if stored := accounts.get(attempt.username):
        if attempt.password_digest == stored.password_digest:
            pass # successful login
        else:
            pass # password doesn't match
    else:
        pass # No account with that name found


@dataclass
class LoginAttempt:
    """A message containing a login attempt.

    The wire encoding of this message is:

    field name          type    size (bytes)
    ----------------------------------------
    Message Type        int     4
    Username Length     int     4
    Username            str     variable (Username Length)
    Password Length     int     4
    Password            str     variable (Password Length)
    Message Terminator          3
    """

    username: str
    password_digest: str

    @classmethod
    def from_network_message(cls: 'Type[LoginAttempt]',
                             msg_payload: bytes) -> 'LoginAttempt':
        raw_message = io.BytesIO(msg_payload)
        msg_type = raw_message.read(INT_SIZE)
        assert msg_type == 2, "Invalid message tag!"

        username_len_raw = raw_message.read(INT_SIZE)
        username_len = int.from_bytes(username_len_raw, byteorder='big')
        assert 0 < username_len <= MAX_USERNAME_SIZE, "Invalid username length!"

        username_raw = raw_message.read(username_len)
        username = str(username_raw, encoding='utf-8')

        password_len_raw = raw_message.read(INT_SIZE)
        password_len = int.from_bytes(password_len_raw, byteorder='big')
        assert 0 < password_len <= MAX_PASSWORD_SIZE, "Invalid password length!"

        password_raw = raw_message.read(password_len)
        password = str(password_raw, encoding='utf-8')
        password_digest = _hash_the_password(password)

        return cls(username, password_digest)


def _hash_the_password(password: str) -> str:
    digest = hashlib.scrypt(password.encode(encoding='utf-8'),
                            salt=SALT,
                            n=16384,
                            r=8,
                            p=1)
    return digest.hex()