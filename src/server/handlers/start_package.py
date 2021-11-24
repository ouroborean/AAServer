import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type
from server.byte_buffer import ByteBuffer
from server.client import client_db
from server.player_status import PlayerStatus
from server.match_manager import manager
from typing import Optional, Tuple
if TYPE_CHECKING:
    from server.managers.accounts import AccountManager, AccountRecord

INT_SIZE = 4
MAX_USERNAME_SIZE = 420
MAX_PASSWORD_SIZE = 420

def handle_start_package(raw_data: bytes, client) -> Optional[Tuple[str, list, list]]:
    package = StartPackage.from_network_message(raw_data)
    if len(manager.waiting_matches) == 0:
        manager.create_open_match(client, package)
        return None
    else:
        mID = manager.close_match(client, package)
        p1_message = get_player1_start_package(mID)
        p2_message = get_player2_start_package(mID)
        return [mID, p1_message, p2_message]

def get_player1_start_package(mID: str) -> list:
    buffer = ByteBuffer()
    buffer.write_int(0)
    if manager.matches[mID].player1_first:
        buffer.write_int(1)
    else:
        buffer.write_int(0)
    for i in manager.matches[mID].player1_energy:
        buffer.write_int(i)
    for character in manager.matches[mID].player2_start_package.characters:
        buffer.write_string(character)
    buffer.write_int(len(manager.matches[mID].player2_start_package.player_package))
    buffer.write_bytes(manager.matches[mID].player2_start_package.player_package)
    buffer.write_byte(b'\x1f\x1f\x1f')
    return buffer.get_byte_array()

def get_player2_start_package(mID: str) -> list:
    buffer = ByteBuffer()       
    buffer.write_int(0)
    if manager.matches[mID].player1_first:
            buffer.write_int(0)
    else:
        buffer.write_int(1)
    for i in manager.matches[mID].player2_energy:
        buffer.write_int(i)
    for character in manager.matches[mID].player1_start_package.characters:
        buffer.write_string(character)
    buffer.write_int(len(manager.matches[mID].player1_start_package.player_package))
    buffer.write_bytes(manager.matches[mID].player1_start_package.player_package)
    buffer.write_byte(b'\x1f\x1f\x1f')
    return buffer.get_byte_array()


@dataclass
class StartPackage:
    """A message containing a player's match starting package.

    The wire encoding of this message is:

    field name              type    size (bytes)
    ----------------------------------------
    Message Type            int     4
    Player Package Length   int     4
    Player Package          bytes   variable (Player Package Length)
    Message Terminator              3
    """
    characters: list
    player_package: bytes

    @classmethod
    def from_network_message(cls: 'Type[StartPackage]',
                             msg_payload: bytes) -> 'StartPackage':
        raw_message = io.BytesIO(msg_payload)
        msg_type = int.from_bytes(raw_message.read(INT_SIZE), 'big')

        assert msg_type == 0, "Invalid message tag!"
        characters = []
        for _ in range(3):
            character_len_raw = raw_message.read(INT_SIZE)
            character_len = int.from_bytes(character_len_raw, byteorder='big')
            character_raw = raw_message.read(character_len)
            character = str(character_raw, encoding = 'utf-8')
            characters.append(character)
        
        player_package_len_raw = raw_message.read(INT_SIZE)
        player_package_len = int.from_bytes(player_package_len_raw, byteorder='big')
        player_package = raw_message.read(player_package_len)

        return cls(characters, player_package)