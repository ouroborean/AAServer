import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type
from server.byte_buffer import ByteBuffer
from typing import Optional, Tuple
if TYPE_CHECKING:
    from server.managers.accounts import AccountManager, AccountRecord
    from server.managers.ranked_matches import RankedMatchManager

INT_SIZE = 4
MAX_USERNAME_SIZE = 420
MAX_PASSWORD_SIZE = 420

def handle_start_package(raw_data: bytes, client, manager: "RankedMatchManager") -> Optional[Tuple[str, list, list]]:

    package = RankedStartPackage.from_network_message(raw_data)
    
    if len(manager.waiting_matches) == 0:
        manager.create_open_match(client, package)
        return None
    else:
        mID = manager.close_match(client, package)
        p1_message = get_player1_start_package(mID, manager)
        p2_message = get_player2_start_package(mID, manager)
        return [mID, p1_message, p2_message]

def get_player1_start_package(mID: str, manager: "RankedMatchManager") -> list:
    buffer = ByteBuffer()
    buffer.write_int(10)
    
    if manager.matches[mID].player1_first:
        buffer.write_int(1)
    else:
        buffer.write_int(0)
    
    package = manager.matches[mID].player2_start_package.player_package

    buffer.write_string(package[0])
    buffer.write_int(package[1])
    buffer.write_int(package[2])
    buffer.write_string(package[3])
    buffer.write_int(package[4])
    buffer.write_int(package[5])
    buffer.write_int(len(package[6]))
    buffer.write_bytes(package[6])
    
    buffer.write_byte(b'\x1f\x1f\x1f')
    return buffer.get_byte_array()

def get_player2_start_package(mID: str, manager: "RankedMatchManager") -> list:
    buffer = ByteBuffer()       
    buffer.write_int(10)
    if manager.matches[mID].player1_first:
            buffer.write_int(0)
    else:
        buffer.write_int(1)
    
    package = manager.matches[mID].player1_start_package.player_package

    buffer.write_string(package[0])
    buffer.write_int(package[1])
    buffer.write_int(package[2])
    buffer.write_string(package[3])
    buffer.write_int(package[4])
    buffer.write_int(package[5])
    buffer.write_int(len(package[6]))
    buffer.write_bytes(package[6])
    buffer.write_byte(b'\x1f\x1f\x1f')
    return buffer.get_byte_array()


@dataclass
class RankedStartPackage:
    """A message containing a player's ranked match starting package.

    The wire encoding of this message is:

    field name              type    size (bytes)
    ----------------------------------------
    Message Type            int     4
    Player Package Length   int     4
    Player Package          bytes   variable (Player Package Length)
    Message Terminator              3
    """
    player_package: list

    @classmethod
    def from_network_message(cls: 'Type[RankedStartPackage]',
                             msg_payload: bytes) -> 'RankedStartPackage':
        raw_message = io.BytesIO(msg_payload)
        msg_type = int.from_bytes(raw_message.read(INT_SIZE), 'big')

        assert msg_type == 12, "Invalid message tag!"
        
        player_package = list()

        player_name_len_raw = raw_message.read(INT_SIZE)
        player_name_len = int.from_bytes(player_name_len_raw, byteorder='big')
        player_name_raw = raw_message.read(player_name_len)
        player_name = str(player_name_raw, encoding = 'utf-8')


        player_wins_raw = raw_message.read(INT_SIZE)
        player_wins = int.from_bytes(player_wins_raw, byteorder='big')

        player_losses_raw = raw_message.read(INT_SIZE)
        player_losses = int.from_bytes(player_losses_raw, byteorder='big')
        

        player_image_mode_len_raw = raw_message.read(INT_SIZE)
        player_image_mode_len = int.from_bytes(player_image_mode_len_raw, byteorder='big')
        player_image_mode_raw = raw_message.read(player_image_mode_len)
        player_image_mode = str(player_image_mode_raw, encoding='utf-8')

        player_image_width_raw = raw_message.read(INT_SIZE)
        player_image_width = int.from_bytes(player_image_width_raw, byteorder='big')

        player_image_height_raw = raw_message.read(INT_SIZE)
        player_image_height = int.from_bytes(player_image_height_raw, byteorder='big')

        player_image_bytes_len_raw = raw_message.read(INT_SIZE)
        player_image_bytes_len = int.from_bytes(player_image_bytes_len_raw, byteorder='big')
        player_image_bytes = raw_message.read(player_image_bytes_len)


        player_package = [player_name, player_wins, player_losses, player_image_mode, player_image_width, player_image_height, player_image_bytes]

        return cls(player_package)