import hashlib
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type
from server.byte_buffer import ByteBuffer

from server.handlers.login import INT_SIZE, MAX_PASSWORD_SIZE, MAX_USERNAME_SIZE
if TYPE_CHECKING:
    from server.managers.accounts import AccountManager, AccountRecord

SALT = b'gawr gura for president'

INT_SIZE = 4
MAX_USERNAME_SIZE = 420
MAX_PASSWORD_SIZE = 420

def handle_register(raw_data: bytes, client, accounts: 'AccountManager') -> list:
    attempt = RegisterAttempt.from_network_message(raw_data)
    if stored := accounts.get(attempt.username):
        return bundle_response("Registration failed: Account already exists.")
    else:
        create_new_data_files(attempt, accounts)
        return bundle_response("Registration complete! Please log in to continue.")


def create_new_data_files(attempt: 'RegisterAttempt', account_manager: 'AccountManager'):
    with open(account_manager._accounts_dir / f"{attempt.username}data.dat", "w") as f:
        f.write("0/0") #TODO: add character mission details
    with open(account_manager._accounts_dir / f"{attempt.username}pass.dat", "w") as f:
        f.write(attempt.password_digest)

def bundle_response(message: str) -> list:
    buffer = ByteBuffer()
    buffer.write_int(4)
    buffer.write_string(message)
    buffer.write_byte(b'\x1f\x1f\x1f')
    return buffer.get_byte_array()


@dataclass
class RegisterAttempt:
    """A message containing a registration attempt.

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
    def from_network_message(cls: 'Type[RegisterAttempt]',
                             msg_payload: bytes) -> 'RegisterAttempt':
        raw_message = io.BytesIO(msg_payload)
        msg_type = int.from_bytes(raw_message.read(INT_SIZE), 'big')

        assert msg_type == 3, "Invalid message tag!"

        username_len_raw = raw_message.read(INT_SIZE)
        username_len = int.from_bytes(username_len_raw, byteorder='big')
        assert 0 < username_len <= MAX_USERNAME_SIZE, "Invalid username length!"

        username_raw = raw_message.read(username_len)
        username = str(username_raw, encoding='utf-8')

        password_len_raw = raw_message.read(INT_SIZE)
        password_len = int.from_bytes(password_len_raw, byteorder='big')
        assert 0 < password_len <= MAX_PASSWORD_SIZE, "Invalid username length!"

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