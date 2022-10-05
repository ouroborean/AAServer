import hashlib
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type
from server.byte_buffer import ByteBuffer

if TYPE_CHECKING:
    from server.managers.accounts import AccountManager

SALT = b'gawr gura for president'

INT_SIZE = 4
MAX_USERNAME_SIZE = 420
MAX_PASSWORD_SIZE = 420

def handle_register(raw_data: bytes, client, accounts: 'AccountManager') -> list:
    attempt = RegisterAttempt.from_network_message(raw_data)
    stored = accounts.get(attempt.username)
    if stored:
        return bundle_response("Registration failed: Account already exists.")
    else:
        create_new_data_files(attempt, accounts)
        return bundle_response("Registration complete! Please log in to continue.")


def create_new_data_files(attempt: 'RegisterAttempt', account_manager: 'AccountManager'):
    with open(account_manager._accounts_dir / f"{attempt.username}data.dat", "w") as f:
        mission_data = [name + "/0/0/0/0/0|" for name in characters]

        mission_data = ""

        free_characters = ["naruto", "ichigo", "tsunayoshi", "saber", "midoriya", "tatsumi", "snowwhite", "natsu", "misaka"]

        for name in characters:
            mission_data += name
            mission_stack = ""
            if name in free_characters:
                mission_stack = "/0/0/0/0/0/1|"
            else:
                mission_stack = "/0/0/0/0/0/1|"
            mission_data += mission_stack

        mission_string = "".join(mission_data)
        mission_string = mission_string[:-1]
        new_data_string = "0/0/15|"
        lines = [new_data_string, mission_string]
        f.writelines(lines)

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

        return cls(username, password)

def _hash_the_password(password: str) -> str:
    digest = hashlib.scrypt(password.encode(encoding='utf-8'),
                            salt=SALT,
                            n=16384,
                            r=8,
                            p=1)
    return digest.hex()



characters = ["naruto",
              "itachi",
              "minato",
              "neji",
              "hinata",
              "shikamaru",
              "kakashi",
              "ichigo",
              "orihime",
              "rukia",
              "ichimaru",
              "aizen",
              "midoriya",
              "toga",
              "mirio",
              "shigaraki",
              "todoroki",
              "uraraka",
              "jiro",
              "natsu",
              "gray",
              "gajeel",
              "wendy",
              "erza",
              "levy",
              "laxus",
              "lucy",
              "saber",
              "jack",
              "chu",
              "astolfo",
              "frankenstein",
              "gilgamesh",
              "jeanne",
              "misaka",
              "kuroko",
              "sogiita",
              "misaki",
              "frenda",
              "naruha",
              "accelerator",
              "tsunayoshi",
              "yamamoto",
              "hibari",
              "gokudera",
              "ryohei",
              "lambo",
              "chrome",
              "tatsumi",
              "mine",
              "akame",
              "leone",
              "raba",
              "sheele",
              "chelsea",
              "seryu",
              "kurome",
              "esdeath",
              "snowwhite",
              "ruler",
              "ripple",
              "nemu",
              "cmary",
              "cranberry",
              "swimswim",
              "pucelle",
              "chachamaru",
              "saitama",
              "tatsumaki",
              "mirai",
              "touka",
              "killua",
              "sheele",
              "byakuya",
              "rikka",
              "anya"]