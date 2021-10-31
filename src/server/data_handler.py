from server.byte_buffer import ByteBuffer
from server.match_manager import manager
from typing import Callable
from server.client import client_db
import os
from os import listdir
from os.path import isfile, join

def handle_login_attempt(data: list, client):
    print("Received login attempt!")
    buffer = ByteBuffer()
    buffer.write_bytes(data)
    buffer.write_bytes(data)
    packet_id = buffer.read_int()
    username = buffer.read_string()
    password = buffer.read_string()

    username = username.replace("\0", "")
    password = password.replace("\0", "")

    buffer.clear()

    if not os.path.exists("accounts"):
        os.makedirs("accounts")
        os.makedirs("accounts/avatars")
    else:
        path = f"accounts/{username}.dat"
        if os.path.exists(path):
            if username in client_db.keys() and client_db[username]:
                send_login_failure(client, "Account currently logged in.")
            else:
                with open(path) as f:
                    lines = f.readlines()
                    if lines[0].strip() == password:
                        client.username = username
                        client_db[client.username] = True
                        ava_code = None
                        if os.path.exists(f"accounts/avatars/{username}.dat"):
                            with open(f"accounts/avatars/{username}.dat", "rb") as ava_f:
                                ava_code = ava_f.read()
                        send_login_confirmation(client, int(lines[1].strip()), int(lines[2].strip()), ava_code)
                    else:
                        send_login_failure(client, "Incorrect password.")
        else:
            send_login_failure(client, "No account exists with that username.")

def send_login_failure(client, message):
    buffer = ByteBuffer()
    buffer.write_int(2)
    buffer.write_string(message)
    client.connection.write(buffer.get_byte_array())
    buffer.clear()
    

def send_login_confirmation(client, wins, losses, avatar=None):
    buffer = ByteBuffer()
    buffer.write_int(3)
    buffer.write_int(wins)
    buffer.write_int(losses)
    if avatar:
        buffer.write_int(len(list(avatar)))
        buffer.write_bytes(list(avatar))
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

    username = username.replace("\0", "")
    password = password.replace("\0", "")

    buffer.clear()

    if not username.isalnum():
        send_registration(client, "Please use alphanumeric characters only.")
    else:
        if not os.path.exists("accounts"):
            os.makedirs("accounts")
        else:
            path = f"accounts/{username}.dat"
            if os.path.exists(path):
                send_registration(client, "Username taken. Please choose another username.")
            else:
                with open(path, "w") as f:
                    f.writelines(password + "\n")
                    f.writelines("0\n")
                    f.writelines("0\n")
                send_registration(client, "Registration complete!")

def handle_player_update(data: list, client):
    buffer = ByteBuffer()
    buffer.write_bytes(data)
    buffer.read_int()
    wins = buffer.read_int()
    losses = buffer.read_int()

    with open(f"accounts/{client.username}.dat") as f:
        lines = f.readlines()
        lines[1] = str(wins) + "\n"
        lines[2] = str(losses) + "\n"
    
    with open(f"accounts/{client.username}.dat", "w") as f:
        for line in lines:
            f.writelines(line)


def send_registration(client, message):
    buffer = ByteBuffer()
    buffer.write_int(4)
    buffer.write_string(message)
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
        send_opponent_package(manager.matches[mID].player1, manager.matches[mID].player2_start_package, True)
        send_opponent_package(manager.matches[mID].player2, manager.matches[mID].player1_start_package, False)

def handle_surrender(data: list, client):
    for match in manager.matches.values():
            if client == match.player1:
                send_surrender_notification(match.player2)
            elif client == match.player2:
                send_surrender_notification(match.player1)

def send_surrender_notification(client):
    buffer = ByteBuffer()
    buffer.write_int(5)

    client.connection.write(buffer.get_byte_array())
    buffer.clear()

def send_opponent_package(client, package, first_turn):
    print("Opponent package sent!")
    buffer = ByteBuffer()
    buffer.write_int(0)
    if first_turn:
        buffer.write_int(1)
    else:
        buffer.write_int(0)
    buffer.write_bytes(package)
    client.connection.write(buffer.get_byte_array())

def handle_match_communication(data: list, client):
    
    buffer = ByteBuffer()
    buffer.write_bytes(data)

    if client == client.match.player1:
        print("Sending communication to player 2!")
        client.match.player2.connection.write(buffer.get_byte_array())
    elif client == client.match.player2:
        print("Sending communication to player 1!")
        client.match.player1.connection.write(buffer.get_byte_array())

    buffer.clear()

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
    7: handle_search_cancellation
}


    

