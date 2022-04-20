import hashlib
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type, Tuple
from server.byte_buffer import ByteBuffer
from server.client import client_db, Client
from server.player_status import PlayerStatus
from server.handlers.register import characters
if TYPE_CHECKING:
    from server.managers.accounts import AccountManager, AccountRecord
    from server.managers.matches import MatchManager

SALT = b'gawr gura for president'

INT_SIZE = 4
MAX_USERNAME_SIZE = 420
MAX_PASSWORD_SIZE = 420



def handle_login(raw_data: bytes, client, accounts: 'AccountManager') -> Tuple[bool, list]:
    attempt = LoginAttempt.from_network_message(raw_data)
    if stored := accounts.get(attempt.username):
        if compare_passwords(attempt, stored, client):
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

def handle_reconnection(client, match_manager: "MatchManager") -> list:
    for match in match_manager.matches.values():
        if match.match_id[0] == client.username or match.match_id[1] == client.username:
            match.rejoin_match(client)
    if client == client.match.player1:
        return get_player1_reconnection_info(client)
    elif client == client.match.player2:
        return get_player2_reconnection_info(client)

def get_player1_reconnection_info(client: Client) -> list:
    buffer = ByteBuffer()
    # Attach reconnection message tag
    buffer.write_int(6)


    # Encode reconnecting player's team/player information
    for name in client.match.player1_start_package.characters:
        buffer.write_string(name)


    # Encode enemy player's player package information
    package = client.match.player2_start_package.player_package

    buffer.write_string(package[0])
    buffer.write_int(package[1])
    buffer.write_int(package[2])
    buffer.write_string(package[3])
    buffer.write_int(package[4])
    buffer.write_int(package[5])
    buffer.write_int(len(package[6]))
    buffer.write_bytes(package[6])


    # Encode enemy player's team/player information
    for name in client.match.player2_start_package.characters:
        buffer.write_string(name)

    # Encode whether player 1 went first or not
    if client.match.player1_first:
        buffer.write_int(1)
    else:
        buffer.write_int(0)
        
    if client.match.player1_turn:
        buffer.write_int(client.match.turn_timer.time_left)
        print(client.match.turn_timer.time_left)
    else:
        buffer.write_int(0)

    # Encode history of ability messages
    buffer.write_int(len(client.match.turn_history))

    for message in client.match.turn_history:
        buffer.write_bytes(message)

    # Encode history of player 1's energy gain pools
    buffer.write_int(len(client.match.player1_energy_history))

    for pool in client.match.player1_energy_history:
        for i in pool:
            buffer.write_int(i)


    # Encode message termination
    buffer.write_byte(b'\x1f\x1f\x1f')
    return buffer.get_byte_array()

def get_player2_reconnection_info(client: Client) -> list:
    buffer = ByteBuffer()
    # Attach reconnection message tag
    buffer.write_int(6)

    # Encode reconnecting player's team/player information
    for name in client.match.player2_start_package.characters:
        buffer.write_string(name)


    # Encode enemy player's player package information
    package = client.match.player1_start_package.player_package

    buffer.write_string(package[0])
    buffer.write_int(package[1])
    buffer.write_int(package[2])
    buffer.write_string(package[3])
    buffer.write_int(package[4])
    buffer.write_int(package[5])
    buffer.write_int(len(package[6]))
    buffer.write_bytes(package[6])


    # Encode enemy player's team/player information
    for name in client.match.player1_start_package.characters:
        buffer.write_string(name)

    # Encode whether player went first or not
    if client.match.player1_first:
        buffer.write_int(0)
    else:
        buffer.write_int(1)

    if client.match.player1_turn:
        buffer.write_int(0)
    else:
        print(client.match.turn_timer.time_left)
        buffer.write_int(client.match.turn_timer.time_left)

    # Encode history of ability messages
    buffer.write_int(len(client.match.turn_history))

    for message in client.match.turn_history:
        buffer.write_bytes(message)

    # Encode history of player 2's energy gain pools
    buffer.write_int(len(client.match.player2_energy_history))

    for pool in client.match.player2_energy_history:
        for i in pool:
            buffer.write_int(i)


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

        return cls(username, password)


def _hash_the_password(password: str) -> str:
    digest = hashlib.scrypt(password.encode(encoding='utf-8'),
                            salt=SALT,
                            n=16384,
                            r=8,
                            p=1)
    return digest.hex()

def nonce_the_digest(digest: str, nonce: int) -> str:
    new_digest = hashlib.scrypt(digest.encode(encoding='utf-8'),
                            salt=str(nonce).encode(encoding='utf-8'),
                            n=16384,
                            r=8,
                            p=1)
    return new_digest.hex()

def compare_passwords(attempt: "LoginAttempt", account: 'AccountRecord', client: Client) -> bool:
    return attempt.password_digest == nonce_the_digest(account.password_digest, client.nonce)
