from server import match
from server.byte_buffer import ByteBuffer
from server.managers.matches import MatchManager
from server.managers.accounts import AccountManager
from pathlib import Path
import sys
import dill as pickle
import os
import random
from typing import TYPE_CHECKING, Callable
from server.handlers import login, match_communication, register, start_package
import asyncio
from server.player_status import PlayerStatus
from server.client import client_db, Client


SALT = b'gawr gura for president'


VERSION = "0.9.8"

class Server:

    accounts: AccountManager
    matches: MatchManager
    packets: dict[int, Callable]

    def __init__(self, data_dir: Path):
        self.matches = MatchManager()
        self.accounts = AccountManager(Path(data_dir))

        self.packets = {
            0: self.handle_start_package,
            1: self.handle_match_communication,
            2: self.handle_login_attempt,
            3: self.handle_registration,
            4: self.handle_avatar_update,
            5: self.handle_player_update,
            6: self.handle_surrender,
            7: self.handle_search_cancellation,
            8: self.handle_match_ending,
            9: self.process_match_stats,
            10: self.handle_version_check
        }


    async def handle_echo(self, reader, writer):
        print("Client connected!")
        client = Client(writer, writer.get_extra_info('peername')[0], writer.get_extra_info('peername')[1])
        buffer = ByteBuffer()
        while True:
            try:
                data = await reader.readuntil(b'\x1f\x1f\x1f')
            except asyncio.exceptions.IncompleteReadError:
                break
            if not data:
                break
            buffer.write_bytes(data[:-3])
            print(f"Package received of length {len(data)}")
            packet_id = buffer.read_int(False)
            self.packets[packet_id](buffer.buff, client)
            buffer.clear()
        if client.username != "":
            print(f"Player {client.username} disconnected from server.")
            if client.match:
                if client == client.match.player1 and self.matches.match_exists(client.match.get_match_id()):
                    if client_db[client.match.player2.username] == PlayerStatus.DISCONNECTED:
                        self.add_a_loss(client)
                        self.add_a_loss(client.match.player2)
                        client_db[client.match.player2.username] = PlayerStatus.OFFLINE
                        client_db[client.username] = PlayerStatus.OFFLINE
                        self.handle_match_ending([], client)
                    else:
                        client_db[client.username] = PlayerStatus.DISCONNECTED
                elif client.match.player2 and client == client.match.player2 and self.matches.match_exists(client.match.get_match_id()):
                    if client_db[client.match.player1.username] == PlayerStatus.DISCONNECTED:
                        self.add_a_loss(client)
                        self.add_a_loss(client.match.player1)
                        client_db[client.match.player1.username] = PlayerStatus.OFFLINE
                        client_db[client.username] = PlayerStatus.OFFLINE
                        self.handle_match_ending([], client)
                    else:
                        client_db[client.username] = PlayerStatus.DISCONNECTED
                else: 
                    client_db[client.username] = PlayerStatus.OFFLINE
            else:
                client_db.pop(client.username)
            for match in self.matches.waiting_matches:
                if match.player1 == client:
                    self.matches.clear_matches()


    def handle_version_check(self, data: list, client: Client):
        print(f"Returning: Version {VERSION}")
        buffer = ByteBuffer()
        buffer.write_int(7)
        buffer.write_string(VERSION)
        buffer.write_byte(b'\x1f\x1f\x1f')
        client.connection.write(buffer.get_byte_array())
        buffer.clear()


    def handle_login_attempt(self, data: list, client: Client):
        # Attempt login and retrieve message to send back to client, either:
        #   A: A successful login package, with player and account information
        #   B: A failure message
        reconnecting, login_result = login.handle_login(bytes(data), client, self.accounts)
        # Send message back to client
        print(len(login_result))
        client.connection.write(login_result)

        # Handle reconnection if the client is shown as having disconnected from a game
        if reconnecting:
            client.connection.write(login.handle_reconnection(client, self.matches))

    def handle_avatar_update(self, data:list, client: Client):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        length = buffer.read_int()
        ava_code = bytes(buffer.read_bytes(length))
        self.accounts.update_avatar(client.username, ava_code)

    def handle_registration(self, data: list, client: Client):
        # Attempt registration and retrieve a response string to send back to the client
        registration_result = register.handle_register(bytes(data), client, account_manager)
        
        # Send response string to client
        client.connection.write(registration_result)


    def process_match_stats(self, data: list, client: Client):
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


    def handle_player_update(self, data: list, client: Client):
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
        self.accounts.update_data(client.username, write_data)

    def add_a_loss(self, client: Client):
        
        data = self.accounts.get_player_data(client.username)
        player_data = data.split("|")
        win_loss = player_data[0].split("/")
        wins = int(win_loss[0])
        losses = int(win_loss[1])
        medals = int(win_loss[2])
        losses += 1
        print(f"Updating {client.username} to W: {wins} / L: {losses}")
        new_record = f"{wins}/{losses}/{medals}"
     
        player_data[0] = new_record
        write_data = "|".join(player_data)
        #TODO add updates to mission data

        self.accounts.update_data(client.username, write_data)

    def handle_start_package(self, data: list, client: Client):
        
        if start_package_response := start_package.handle_start_package(bytes(data), client, self.matches):
            mID = start_package_response[0]
            p1_message = start_package_response[1]
            p2_message = start_package_response[2]
            self.matches.send_player1_message(mID, p1_message)
            self.matches.send_player2_message(mID, p2_message)

    def handle_surrender(self, data: list, client: Client):
            if client == client.match.player1:
                self.send_surrender_notification(client.match.player2, data)
            elif client == client.match.player2:
                self.send_surrender_notification(client.match.player1, data)
            self.handle_match_ending([], client)

    def send_surrender_notification(self, client: Client, data: bytes):

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

    def handle_match_communication(self, data: list, client: Client):
        
        message = match_communication.handle_match_communication(bytes(data), client)

        if client == client.match.player1:
            client.match.player2.connection.write(message)
        elif client == client.match.player2:
            client.match.player1.connection.write(message)
        else:
            pass #TODO: add custom error


    def handle_match_ending(self, data: list, client: Client):
        self.matches.end_match(client.match.get_match_id())

    def handle_search_cancellation(self, data: list, client: Client):
        self.matches.clear_matches()
