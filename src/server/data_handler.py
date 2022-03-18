from server import match
from server.byte_buffer import ByteBuffer
from server.match_manager import manager
from server.managers.accounts import AccountManager
from pathlib import Path
import sys
import dill as pickle
import os
import random

from server.handlers import login, match_communication, register, start_package

SALT = b'gawr gura for president'

account_manager = AccountManager(Path(r"C:\Users\poofl\Documents\Code\AAServer"))

VERSION = "0.9.8"

def handle_version_check(data: list, client):
    print(f"Returning: Version {VERSION}")
    buffer = ByteBuffer()
    buffer.write_int(7)
    buffer.write_string(VERSION)
    buffer.write_byte(b'\x1f\x1f\x1f')
    client.connection.write(buffer.get_byte_array())
    buffer.clear()


def handle_login_attempt(data: list, client):
    # Attempt login and retrieve message to send back to client, either:
    #   A: A successful login package, with player and account information
    #   B: A failure message
    reconnecting, login_result = login.handle_login(bytes(data), client, account_manager)
    # Send message back to client
    print(len(login_result))
    client.connection.write(login_result)

    # Handle reconnection if the client is shown as having disconnected from a game
    if reconnecting:
        client.connection.write(login.handle_reconnection(client))

def handle_avatar_update(data:list, client):
    buffer = ByteBuffer()
    buffer.write_bytes(data)
    buffer.read_int()
    length = buffer.read_int()
    ava_code = bytes(buffer.read_bytes(length))
    with open(account_manager._avatars_dir / f"{client.username}.dat", "wb") as f:
        f.write(ava_code)

def handle_registration(data: list, client):
    # Attempt registration and retrieve a response string to send back to the client
    registration_result = register.handle_register(bytes(data), client, account_manager)
    
    # Send response string to client
    client.connection.write(registration_result)


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
    medals = buffer.read_int()
    missions = buffer.read_string()
    print(f"Updating {client.username} to W: {wins} / L: {losses}")
    data = f"{wins}/{losses}/{medals}"
    write_data = data + "|" + missions
    with open(account_manager._accounts_dir / f"{client.username}data.dat", "w") as f:
        f.write(write_data)

def add_a_loss(client):
    with open(f"accounts/{client.username}data.dat") as f:
        data = f.read().strip()
        player_data = data.split("|")
        win_loss = player_data[0].split("/")
        wins = int(win_loss[0])
        losses = int(win_loss[1])
        medals = int(win_loss[2])
        losses += 1
        print(f"Updating {client.username} to W: {wins} / L: {losses}")
        data = f"{wins}/{losses}/{medals}"
    
    with open(account_manager._accounts_dir / f"{client.username}data.dat", "r") as f:
        player_data = f.read().split("|")
        player_data[0] = data
        write_data = "|".join(player_data)
        #TODO add updates to mission data

    with open(account_manager._accounts_dir / f"{client.username}data.dat", "w") as f:
        f.write(write_data)

def handle_start_package(data: list, client):
    
    if start_package_response := start_package.handle_start_package(bytes(data), client):
        mID = start_package_response[0]
        p1_message = start_package_response[1]
        p2_message = start_package_response[2]
        manager.matches[mID].player1.connection.write(p1_message)
        manager.matches[mID].player2.connection.write(p2_message)

def handle_surrender(data: list, client):
        if client == client.match.player1:
            send_surrender_notification(client.match.player2, data)
        elif client == client.match.player2:
            send_surrender_notification(client.match.player1, data)
        handle_match_ending([], client)

def send_surrender_notification(client, data: bytes):

    temp_buffer = ByteBuffer()
    temp_buffer.write_bytes(data)
    temp_buffer.read_int()
    mission_packages = []
    for _ in range(3):
            mission_package = [temp_buffer.read_int() for _ in range(5)]
            mission_packages.append(mission_package)



    buffer = ByteBuffer()
    buffer.write_int(5)

    for mission_progress_package in mission_packages:
            for mission_progress in mission_progress_package:
                buffer.write_int(mission_progress)

    buffer.write_byte(b'\x1f\x1f\x1f')

    client.connection.write(buffer.get_byte_array())
    buffer.clear()

def handle_match_communication(data: list, client):
    
    message = match_communication.handle_match_communication(bytes(data), client)

    if client == client.match.player1:
        client.match.player2.connection.write(message)
    elif client == client.match.player2:
        client.match.player1.connection.write(message)
    else:
        pass #TODO: add custom error


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
    9: process_match_stats,
    10: handle_version_check
}


    

