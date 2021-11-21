from server.byte_buffer import ByteBuffer
from server.match_manager import manager
from server.player_status import PlayerStatus
from typing import Callable
from server.client import client_db
import dill as pickle
import os
import random
import hashlib
from os import listdir
from os.path import isfile, join
SALT = b'gawr gura for president'

def handle_login_attempt(data: list, client):
    print("Received login attempt!")
    buffer = ByteBuffer()
    buffer.write_bytes(data)
    buffer.write_bytes(data)
    packet_id = buffer.read_int()
    username = buffer.read_string()
    password = buffer.read_string()
    password = bytes(password, 'utf-16')
    hashpass = hashlib.scrypt(password, salt=SALT, n=16384, r=8, p=1)   
    buffer.clear()

    if not os.path.exists("accounts"):
        os.makedirs("accounts")
        os.makedirs("accounts/avatars")
    else:
        path = f"accounts/{username}.dat"
        if os.path.exists(path):
            if username in client_db.keys() and (client_db[username] == PlayerStatus.ONLINE or client_db[username] == PlayerStatus.DISCONNECTED):
                if client_db[username] == PlayerStatus.ONLINE:
                    send_login_failure(client, "Account currently logged in.")
                elif client_db[username] == PlayerStatus.DISCONNECTED:
                    for match in manager.matches.values():
                        if match.match_id[0] == username or match.match_id[1] == username:
                            with open(f"accounts/{username}pass.dat", "rb") as f:
                                passhash = f.readline()
                            with open(path) as f:
                                lines = f.readlines()
                            
                                if passhash == hashpass:
                                    client.username = username
                                    client_db[client.username] = PlayerStatus.ONLINE
                                    ava_code = None
                                    if os.path.exists(f"accounts/avatars/{username}.dat"):
                                        with open(f"accounts/avatars/{username}.dat", "rb") as ava_f:
                                            ava_code = ava_f.read()
                                    match.rejoin_match(client)
                                    print("Performed reconnect login!")
                                    send_login_confirmation(client, int(lines[0].strip()), int(lines[1].strip()), ava_code)
                                    send_reconnection(client)
                                else:
                                    send_login_failure(client, "Incorrect password.")
                            
                            
            else:
                with open(f"accounts/{username}pass.dat", "rb") as f:
                    passhash = f.readline()
                with open(path) as f:
                    lines = f.readlines()
                    if passhash == hashpass:
                        client.username = username
                        client_db[client.username] = PlayerStatus.ONLINE
                        ava_code = None
                        if os.path.exists(f"accounts/avatars/{username}.dat"):
                            with open(f"accounts/avatars/{username}.dat", "rb") as ava_f:
                                ava_code = ava_f.read()
                        send_login_confirmation(client, int(lines[0].strip()), int(lines[1].strip()), ava_code)
                    else:
                        send_login_failure(client, "Incorrect password.")
        else:
            send_login_failure(client, "No account exists with that username.")

def send_login_failure(client, message):
    buffer = ByteBuffer()
    buffer.write_int(2)
    buffer.write_string(message)
    buffer.write_byte(b'\x1f\x1f\x1f')
    client.connection.write(buffer.get_byte_array())
    buffer.clear()
    
def send_reconnection(client):
    buffer = ByteBuffer()
    buffer.write_int(6)
    if client == client.match.player1:
        print("Sending reconnection to Player 1!")
        buffer.write_bytes(client.match.player1_start_package)
        if client.match.player1_turn:
            buffer.write_int(1)
        else:
            buffer.write_int(0)
        if client.match.player1_package:
            buffer.write_int(1)
        else:
            buffer.write_int(0)
        for i in client.match.player1_energy:
            buffer.write_int(i)
        buffer.write_bytes(client.match.player2_start_package)
        if client.match.last_package:        
            buffer.write_int(1)
            buffer.write_bytes(client.match.last_package)
        else:
            buffer.write_int(0)
        buffer.write_byte(b'\x1f\x1f\x1f')
        client.connection.write(buffer.get_byte_array())
    elif client == client.match.player2:
        print("Sending reconnection to Player 2!")
        buffer.write_bytes(client.match.player2_start_package)
        if client.match.player1_turn:
            buffer.write_int(0)
        else:
            buffer.write_int(1)
        if client.match.player1_package:
            buffer.write_int(0)
        else:
            buffer.write_int(1)
        for i in client.match.player2_energy:
            buffer.write_int(i)
        buffer.write_bytes(client.match.player1_start_package)
        if client.match.last_package:        
            buffer.write_int(1)
            buffer.write_bytes(client.match.last_package)
        else:
            buffer.write_int(0)
        buffer.write_byte(b'\x1f\x1f\x1f')
        client.connection.write(buffer.get_byte_array())
    buffer.clear()

def send_login_confirmation(client, wins, losses, avatar=None):
    buffer = ByteBuffer()
    buffer.write_int(3)
    buffer.write_int(wins)
    buffer.write_int(losses)
    if avatar:
        buffer.write_int(1)
        buffer.write_int(len(list(avatar)))
        buffer.write_bytes(list(avatar))
    else:
        buffer.write_int(0)
    buffer.write_byte(b'\x1f\x1f\x1f')
    #TODO: Add character unlock information
    client.connection.write(buffer.get_byte_array())
    buffer.clear()

def handle_avatar_update(data:list, client):
    buffer = ByteBuffer()
    buffer.write_bytes(data)
    buffer.read_int()
    length = buffer.read_int()
    ava_code = bytes(buffer.read_bytes(length))
    with open(f"accounts/avatars/{client.username}.dat", "wb") as f:
        f.write(ava_code)

def handle_registration(data: list, client):

    buffer = ByteBuffer()
    buffer.write_bytes(data)
    packet_id = buffer.read_int()
    username = buffer.read_string()
    password = buffer.read_string()
    password = bytes(password, 'utf-16')
    hashpass = hashlib.scrypt(password, salt=SALT, n=16384, r=8, p=1)
    buffer.clear()

    if not username.isalnum():
        send_registration(client, "Please use alphanumeric characters only.")
    else:
        if not os.path.exists("accounts"):
            os.makedirs("accounts")
        else:
            path = f"accounts/{username}pass.dat"
            if os.path.exists(path):
                send_registration(client, "Username taken. Please choose another username.")
            else:
                with open(path, "wb") as f:
                    f.write(hashpass)
                path = f"accounts/{username}.dat"
                with open(path, "w") as f:
                    f.writelines("0\n")
                    f.writelines("0\n")
                send_registration(client, "Registration complete!")

def process_match_stats(data: list, client):
    buffer = ByteBuffer()
    buffer.write_bytes(data)
    buffer.read_int()
    names = [buffer.read_string() for i in range(3)]
    won = buffer.read_int()
    for name in names:
        path = f"stats/{name}.dat"
        if os.path.exists(path):
            with open(path) as f:
                lines = f.readlines()
                played = int(lines[0].strip())
                wins = int(lines[1].strip())
                losses = int(lines[2].strip())
                played += 1
                if won:
                    wins += 1
                else:
                    losses += 1
                lines[0] = str(played) + "\n"
                lines[1] = str(wins) + "\n"
                lines[2] = str(losses) + "\n"
            with open(path, "w") as f:
                for line in lines:
                    f.writelines(line)
        else:
            with open(path, "w") as f:
                if won:
                    wins = 1
                    losses = 0
                else:
                    wins = 0
                    losses = 1
                lines = [1, wins, losses]
                for line in lines:
                    f.writelines(str(line) + "\n")
    buffer.clear()


def handle_player_update(data: list, client):
    buffer = ByteBuffer()
    buffer.write_bytes(data)
    buffer.read_int()
    wins = buffer.read_int()
    losses = buffer.read_int()

    with open(f"accounts/{client.username}.dat") as f:
        lines = f.readlines()
        lines[0] = str(wins) + "\n"
        lines[1] = str(losses) + "\n"
    
    with open(f"accounts/{client.username}.dat", "w") as f:
        for line in lines:
            f.writelines(line)

def add_a_loss(client):
    with open(f"accounts/{client.username}.dat") as f:
        lines = f.readlines()
        losses = int(lines[1].strip())
        lines[1] = str(losses + 1) + "\n"
    
    with open(f"accounts/{client.username}.dat", "w") as f:
        for line in lines:
            f.writelines(line)

def send_registration(client, message):
    buffer = ByteBuffer()
    buffer.write_int(4)
    buffer.write_string(message)
    buffer.write_byte(b'\x1f\x1f\x1f')
    client.connection.write(buffer.get_byte_array())
    buffer.clear()

def handle_start_package(data: list, client):
    print("Received a start package!")
    buffer = ByteBuffer()
    buffer.write_bytes(data)
    packet_id = buffer.read_int()
    start_package = buffer.buff[buffer.read_pos:]
    buffer.clear()

    if len(manager.waiting_matches) == 0:
        print("Created an open match!")
        manager.create_open_match(client, start_package)
    else:
        print("Closed a match!")
        mID = manager.close_match(client, start_package)

        

        send_opponent_package(manager.matches[mID].player1, manager.matches[mID].player1_energy, manager.matches[mID].player2_start_package, manager.matches[mID].player1_first)
        send_opponent_package(manager.matches[mID].player2, manager.matches[mID].player2_energy, manager.matches[mID].player1_start_package, not manager.matches[mID].player1_first)

def handle_surrender(data: list, client):
    for match in manager.matches.values():
            if client == match.player1:
                send_surrender_notification(match.player2)
            elif client == match.player2:
                send_surrender_notification(match.player1)

def send_surrender_notification(client):
    buffer = ByteBuffer()
    buffer.write_int(5)
    buffer.write_byte(b'\x1f\x1f\x1f')

    client.connection.write(buffer.get_byte_array())
    buffer.clear()

def send_opponent_package(client, energy, package, first_turn):
    print("Opponent package sent!")
    buffer = ByteBuffer()
    buffer.write_int(0)
    if first_turn:
        buffer.write_int(1)
    else:
        buffer.write_int(0)
    for i in energy:
        buffer.write_int(i)
    buffer.write_bytes(package)
    buffer.write_byte(b'\x1f\x1f\x1f')
    client.connection.write(buffer.get_byte_array())

def handle_match_communication(data: list, client):
    
    buffer = ByteBuffer()
    buffer.write_bytes(data)
    print(f"Transferring match communication of length {len(data)}")
    buffer.read_int()
    energy_pool = []
    for i in range(4):
        energy_pool.append(buffer.read_int())
    energy_cont = []
    for i in range(5):
        energy_cont.append(buffer.read_int())
    match_data = bytes(buffer.buff[buffer.read_pos:])
    client.match.player1_turn = not client.match.player1_turn
    if client.match.player1_turn:
        print(f"It's {client.match.player1.username}'s turn!")
    else:
        print(f"It's {client.match.player2.username}'s turn!")
    buffer.clear()
    buffer.write_byte(b'\x1f\x1f\x1f')

    if client == client.match.player1:
        client.match.player1_energy = energy_pool
        print("Sending communication to player 2!")
        client.match.first_turn -= 1
        if client.match.first_turn < 0:
            client.match.first_turn = 0
        if not client.match.first_turn:
            client.match.player2_energy = generate_energy(energy_cont, client.match.player2_energy)
        
            
        buffer = ByteBuffer()
        buffer.write_int(1)
        for i in client.match.player2_energy:
            buffer.write_int(i)
        client.match.last_package = match_data
        client.match.player1_package = True
        buffer.write_bytes(match_data)
        buffer.write_byte(b'\x1f\x1f\x1f')
        client.match.player2.connection.write(buffer.get_byte_array())
    elif client == client.match.player2:
        client.match.player2_energy = energy_pool
        print("Sending communication to player 1!")
        client.match.first_turn -= 1
        if client.match.first_turn < 0:
            client.match.first_turn = 0
        if not client.match.first_turn:
            client.match.player1_energy = generate_energy(energy_cont, client.match.player1_energy)
        buffer = ByteBuffer()
        buffer.write_int(1)
        for i in client.match.player1_energy:
            buffer.write_int(i)
        client.match.last_package = match_data
        client.match.player1_package = False
        buffer.write_bytes(match_data)
        buffer.write_byte(b'\x1f\x1f\x1f')
        client.match.player1.connection.write(buffer.get_byte_array())

    buffer.clear()

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


def handle_match_ending(data: list, client):
    manager.matches.pop(client.match.get_match_id())

def handle_search_cancellation(data: list, client):
    manager.waiting_matches.clear()



packets: dict = {
    0: handle_start_package,
    1: handle_match_communication,
    2: handle_login_attempt,
    3: handle_registration,
    4: handle_avatar_update,
    5: handle_player_update,
    6: handle_surrender,
    7: handle_search_cancellation,
    8: handle_match_ending,
    9: process_match_stats
}


    

