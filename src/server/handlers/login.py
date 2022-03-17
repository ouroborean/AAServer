import hashlib
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type, Tuple
from server.byte_buffer import ByteBuffer
from server.client import client_db
from server.player_status import PlayerStatus
from server.match_manager import manager
from server.handlers.register import characters
if TYPE_CHECKING:
    from server.managers.accounts import AccountManager, AccountRecord

SALT = b'gawr gura for president'

INT_SIZE = 4
MAX_USERNAME_SIZE = 420
MAX_PASSWORD_SIZE = 420


def handle_login(raw_data: bytes, client, accounts: 'AccountManager') -> Tuple[bool, list]:
    attempt = LoginAttempt.from_network_message(raw_data)
    if stored := accounts.get(attempt.username):
        if attempt.password_digest == stored.password_digest:
            if stored.username in client_db and client_db[stored.username] == PlayerStatus.ONLINE:
                return bundle_login_failure("Account currently logged in.")
            else:
                client.username = stored.username
                reconnecting = (client.username in client_db and client_db[client.username] == PlayerStatus.DISCONNECTED)
                client_db[client.username] = PlayerStatus.ONLINE
                return [reconnecting, get_player_info(stored)]
        else:
            return bundle_login_failure("No account with matching credentials found.")
    else:
        return bundle_login_failure("No account with matching credentials found.")

def handle_reconnection(client) -> list:
    for match in manager.matches.values():
        if match.match_id[0] == client.username or match.match_id[1] == client.username:
            match.rejoin_match(client)
    if client == client.match.player1:
        return get_player1_reconnection_info(client)
    elif client == client.match.player2:
        return get_player2_reconnection_info(client)

def get_player1_reconnection_info(client) -> list:
    buffer = ByteBuffer()
    # Attach reconnection message tag
    buffer.write_int(6)

    # Encode reconnecting player's team/player information
    for name in client.match.player1_start_package.characters:
        buffer.write_string(name)
    buffer.write_int(len(client.match.player1_start_package.player_package))
    buffer.write_bytes(client.match.player1_start_package.player_package)

    # Encode information regarding whose turn it currently is
    # and the owner of the last turn data the server received
    if client.match.player1_turn:
        buffer.write_int(1)
    else:
        buffer.write_int(0)
    if client.match.player1_package:
        buffer.write_int(1)
    else:
        buffer.write_int(0)

    # Encode the player's energy pool
    for i in client.match.player1_energy:
        buffer.write_int(i)
    
    # Encode enemy player's team/player information
    for name in client.match.player2_start_package.characters:
        buffer.write_string(name)
    buffer.write_int(len(client.match.player2_start_package.player_package))
    buffer.write_bytes(client.match.player2_start_package.player_package)

    # If the server has received ANY turns, encode a tag denoting
    # the existence of (or lack thereof) turn information, then that
    # turn information if it exists
    if client.match.last_package:
        buffer.write_int(1)
        buffer.write_bytes(client.match.last_package)
    else:
        buffer.write_int(0)

    # Encode message termination
    buffer.write_byte(b'\x1f\x1f\x1f')

    return buffer.get_byte_array()

def get_player2_reconnection_info(client) -> list:
    buffer = ByteBuffer()
    # Attach reconnection message tag
    buffer.write_int(6)

    # Encode reconnecting player's team/player information
    for name in client.match.player2_start_package.characters:
        buffer.write_string(name)
    buffer.write_int(len(client.match.player2_start_package.player_package))
    buffer.write_bytes(client.match.player2_start_package.player_package)

    # Encode information regarding whose turn it currently is
    # and the owner of the last turn data the server received
    if client.match.player1_turn:
        buffer.write_int(0)
    else:
        buffer.write_int(1)
    if client.match.player1_package:
        buffer.write_int(0)
    else:
        buffer.write_int(1)

    # Encode the player's energy pool
    for i in client.match.player2_energy:
        buffer.write_int(i)
    
    # Encode enemy player's team/player information
    for name in client.match.player1_start_package.characters:
        buffer.write_string(name)
    buffer.write_int(len(client.match.player1_start_package.player_package))
    buffer.write_bytes(client.match.player1_start_package.player_package)

    # If the server has received ANY turns, encode a tag denoting
    # the existence of (or lack thereof) turn information, then that
    # turn information if it exists
    if client.match.last_package:
        buffer.write_int(1)
        buffer.write_bytes(client.match.last_package)
    else:
        buffer.write_int(0)

    # Encode message termination
    buffer.write_byte(b'\x1f\x1f\x1f')
    
    return buffer.get_byte_array()


def check_for_new_character_info(mission_data):
    characters_to_add = []
    mission_dict = {}
    for mission_set in mission_data.split("|"):
        missions = mission_set.split("/")
        mission_dict[missions[0]] = []
    for character in characters:
        if not character in mission_dict:
            characters_to_add.append(character)
    
    for character in characters_to_add:
        mission_data = mission_data + "|" + character + "/0/0/0/0/0/0"
    
    return mission_data

def get_player_info(account: 'AccountRecord') -> list:
    buffer = ByteBuffer()
    buffer.write_int(3)
    player_data = account.user_data.split("|")
    wins, losses, medals = player_data[0].split("/")
    mission_data = "|".join(player_data[1:]).strip()
    mission_data = check_for_new_character_info(mission_data)
    buffer.write_int(int(wins))
    buffer.write_int(int(losses))
    buffer.write_int(int(medals))
    buffer.write_string(mission_data)
    if account.avatar_file:
        buffer.write_int(1)
        with open(account.avatar_file, "rb") as f:
            ava_code = f.read()
        buffer.write_int(len(ava_code))
        buffer.write_bytes(ava_code)
    else:
        buffer.write_int(0)
    buffer.write_byte(b'\x1f\x1f\x1f')
    return buffer.get_byte_array()

def bundle_login_failure(message: str) -> Tuple[bool, list]:
    buffer = ByteBuffer()
    buffer.write_int(2)
    buffer.write_string(message)
    buffer.write_byte(b'\x1f\x1f\x1f')
    return [False, buffer.get_byte_array()]

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
        msg_type = int.from_bytes(raw_message.read(INT_SIZE), 'big')
        
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