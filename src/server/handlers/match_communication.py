import hashlib
import io
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type
from server.byte_buffer import ByteBuffer
from server.match import Match
from server.match_manager import manager


INT_SIZE = 4

def handle_match_communication(raw_data: bytes, client) -> list:
    communication = MatchCommunication.from_network_message(raw_data)
    client.match.last_package = communication.turn_data
    client.match.player1_turn = not client.match.player1_turn
    client.match.first_turn -= 1
    if client.match.first_turn < 0:
        client.match.first_turn = 0
    if client == client.match.player1:
        process_player1_turn(communication, client)
        return package_player2_message(communication, client)
    elif client == client.match.player2:
        process_player2_turn(communication, client)
        return package_player1_message(communication, client)
    else:
        pass #TODO: add custom error

def process_player1_turn(communication: 'MatchCommunication', client):
    client.match.player1_energy = communication.player_energy
    client.match.player1_package = True
    if not client.match.first_turn:
        client.match.player2_energy = generate_energy(communication.enemy_energy_cont, client.match.player2_energy)

def process_player2_turn(communication: 'MatchCommunication', client):
    client.match.player2_energy = communication.player_energy
    client.match.player1_package = False
    if not client.match.first_turn:
        client.match.player1_energy = generate_energy(communication.enemy_energy_cont, client.match.player1_energy)

def package_player2_message(communication: 'MatchCommunication', client) -> list:
    buffer = ByteBuffer()
    buffer.write_int(1)
    for i in client.match.player2_energy:
        buffer.write_int(i)
    buffer.write_int(len(communication.turn_data))
    buffer.write_bytes(communication.turn_data)
    buffer.write_byte(b'\x1f\x1f\x1f')
    return buffer.get_byte_array()


def package_player1_message(communication: 'MatchCommunication', client) -> list:
    buffer = ByteBuffer()
    buffer.write_int(1)
    for i in client.match.player1_energy:
        buffer.write_int(i)
    buffer.write_int(len(communication.turn_data))
    buffer.write_bytes(communication.turn_data)
    buffer.write_byte(b'\x1f\x1f\x1f')
    return buffer.get_byte_array()

def generate_energy(energy_cont, energy):
    for i in range(4):
        energy[i] += energy_cont[i]
    if energy_cont[4] > 0:
        for i in range(energy_cont[4]):
            energy[random.randint(0,3)] += 1
    else:
        drain = -energy_cont[4]
        while drain > 0:
            e_type = random.randint(0,3)
            if energy[e_type] > 0:
                energy[e_type] -= 1
                drain -= 1
    return energy

@dataclass
class MatchCommunication:
    """A message containing a login attempt.

    The wire encoding of this message is:

    field name          type    size (bytes)
    ----------------------------------------
    Message Type        int     4
    Physical Pool       int     4
    Special Pool        int     4
    Mental Pool         int     4
    Weapon Pool         int     4
    Enemy Phys Cont.    int     4
    Enemy Spec Cont.    int     4
    Enemy Ment Cont.    int     4
    Enemy Wep Cont.     int     4
    Enemy Rand Cont.    int     4
    Turn Package Length int     4
    Turn Package        bytes   variable (Turn Package Length)
    Message Terminator          3
    """

    player_energy: list
    enemy_energy_cont: list
    turn_data: bytes

    @classmethod
    def from_network_message(cls: 'Type[MatchCommunication]', msg_payload: bytes) -> 'MatchCommunication':
        raw_message = io.BytesIO(msg_payload)
        msg_type = int.from_bytes(raw_message.read(INT_SIZE), 'big')

        assert msg_type == 1, "Invalid message tag!"
        
        player_energy = []
        enemy_energy_cont = []
        for _ in range(4):
            energy_raw = raw_message.read(INT_SIZE)
            energy = int.from_bytes(energy_raw, byteorder='big')
            player_energy.append(energy)
        
        for _ in range(5):
            enemy_cont_raw = raw_message.read(INT_SIZE)
            enemy_cont = int.from_bytes(enemy_cont_raw, byteorder='big')
            enemy_energy_cont.append(enemy_cont)

        turn_data_len_raw = raw_message.read(INT_SIZE)
        turn_data_len = int.from_bytes(turn_data_len_raw, byteorder='big')
        turn_data = raw_message.read(turn_data_len)

        return cls(player_energy, enemy_energy_cont, turn_data)

