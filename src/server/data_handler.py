
from server.byte_buffer import ByteBuffer
from server.managers.quick_matches import QuickMatchManager
from server.managers.accounts import AccountManager
from pathlib import Path
import dill as pickle
from functools import partial
import os
import random
from typing import TYPE_CHECKING, Callable
from server.handlers import login, qm_start_package, ranked_start_package, register
import asyncio
import time
from server.managers.ranked_matches import RankedMatchManager
from server.match import RankedMatch, QuickMatch
from server.player_status import PlayerStatus
from server.client import client_db, Client
import logging

SALT = b'gawr gura for president'


VERSION = "0.9.95"

class Server:

    accounts: AccountManager
    q_matches: QuickMatchManager
    r_matches: RankedMatchManager
    packets: dict[int, Callable]
    
    
    def __init__(self, data_dir: Path):
        self.q_matches = QuickMatchManager()
        self.r_matches = RankedMatchManager()
        self.accounts = AccountManager(Path(data_dir))
        self._stats_directory = Path(data_dir) / 'stats'

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
            10: self.handle_version_check,
            11: self.handle_nonce_request,
            12: self.handle_ranked_start_package,
            13: self.handle_draft_message,
            14: self.handle_draft_finalization
        }

    def assign_server(self, server):
        self.server = server

    def process_message(self, buffer, client):
        print(buffer.buff)
        message_id = buffer.read_int()
        if not client.message_in_order(message_id, buffer.buff):
            self.send_message_resend_request(message_id, client)
        buffer.reset_read_pos()
        
        buffer.buff = buffer.buff[4:]
        return buffer.buff
    
    def send_message_resend_request(self, message_id, client):
        buffer = ByteBuffer()
        buffer.write_int(15)
        buffer.write_int(message_id)
        buffer.write_byte(b'\x1f\x1f\x1f')
        client.connection.write(buffer.get_byte_array())

    async def handle_echo(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
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
            buffer.buff = self.process_message(buffer, client)
            packet_id = buffer.read_int(False)
            try:
                self.packets[packet_id](buffer.buff, client)
            except KeyError:
                logging.debug(f"Invalid packet id: {packet_id}")
            buffer.clear()
            # if client.match is truthy, the client must have a match
            # if the client has a match, then there must be an existing turn-timer running
            # If the client is the current player (client == client.match.player1 and client.match.player1_turn)
            #                                                           or
            #                                     (client == client.match.player2 and not client.match.player1_turn)
            # Check the timeout status of the match
            # If timed_out is true, run timeout_handling function
        
        if client.username != "":
            print(f"Player {client.username} disconnected from server.")
            if client.match:
                if client == client.match.player1:
                    if self.q_matches.match_exists(client.match.get_match_id()):
                        if client_db[client.match.player2.username] == PlayerStatus.DISCONNECTED:
                            client_db[client.match.player2.username] = PlayerStatus.OFFLINE
                            client_db[client.username] = PlayerStatus.OFFLINE
                            self.handle_match_ending([], client)
                        else:
                            client_db[client.username] = PlayerStatus.DISCONNECTED
                    elif self.r_matches.match_exists(client.match.get_match_id()):
                        if client.match.drafting:
                            self.send_draft_disconnection(client.match.player2)
                            self.r_matches.end_match(client.match.get_match_id())
                            client_db[client.username] = PlayerStatus.OFFLINE
                        else:
                            if client_db[client.match.player2.username] == PlayerStatus.DISCONNECTED:
                                client_db[client.match.player2.username] = PlayerStatus.OFFLINE
                                client_db[client.username] = PlayerStatus.OFFLINE
                                self.handle_match_ending([], client)
                            else:
                                client_db[client.username] = PlayerStatus.DISCONNECTED
                elif client.match.player2 and client == client.match.player2:
                    if self.q_matches.match_exists(client.match.get_match_id()):
                        if client_db[client.match.player1.username] == PlayerStatus.DISCONNECTED:
                            client_db[client.match.player1.username] = PlayerStatus.OFFLINE
                            client_db[client.username] = PlayerStatus.OFFLINE
                            self.handle_match_ending([], client)
                        else:
                            client_db[client.username] = PlayerStatus.DISCONNECTED
                    elif self.r_matches.match_exists(client.match.get_match_id()):
                        if client.match.drafting:
                            self.send_draft_disconnection(client.match.player1)
                            self.r_matches.end_match(client.match.get_match_id())
                            client_db[client.username] = PlayerStatus.OFFLINE
                        else:
                            if client_db[client.match.player1.username] == PlayerStatus.DISCONNECTED:
                                client_db[client.match.player1.username] = PlayerStatus.OFFLINE
                                client_db[client.username] = PlayerStatus.OFFLINE
                                self.handle_match_ending([], client)
                            else:
                                client_db[client.username] = PlayerStatus.DISCONNECTED
                else:
                    client_db[client.username] = PlayerStatus.OFFLINE
            else:
                client_db.pop(client.username)
            self.q_matches.end_open_match_by_player_name(client)
            self.r_matches.end_open_match_by_player_name(client)
        writer.close()
                    

    def handle_nonce_request(self, data: list, client: Client):
        buffer = ByteBuffer()
        buffer.write_int(9)
        nonce = int(time.time())
        buffer.write_int(nonce)
        buffer.write_byte(b'\x1f\x1f\x1f')
        client.nonce = nonce
        client.connection.write(buffer.get_byte_array())
    
    def handle_draft_finalization(self, data: list, client: Client):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        characters = list()
        for i in range(3):
            characters.append(buffer.read_string())
        client.match.drafting = False
        buffer.clear()
        buffer.write_int(12)
        buffer.write_int(client.match.random_seed)
        if client == client.match.player1:
            client.match.player1_characters = characters
            for i in client.match.player1_energy_history[0]:
                buffer.write_int(i)
            buffer.write_byte(b'\x1f\x1f\x1f')
            client.connection.write(buffer.get_byte_array())
        elif client == client.match.player2:
            client.match.player2_characters = characters
            for i in client.match.player2_energy_history[0]:
                buffer.write_int(i)
            buffer.write_byte(b'\x1f\x1f\x1f')
            client.connection.write(buffer.get_byte_array())
    
    def send_draft_disconnection(self, client: Client):
        buffer = ByteBuffer()
        buffer.write_int(14)
        buffer.write_byte(b'\x1f\x1f\x1f')
        client.connection.write(buffer.get_byte_array())
        buffer.clear()

    def send_timeout(self, client: Client):
        buffer = ByteBuffer()
        buffer.write_int(8)
        buffer.write_byte(b'\x1f\x1f\x1f')
        client.connection.write(buffer.get_byte_array())
        buffer.clear()
        
    def handle_draft_timeout(self, client):
        buffer = ByteBuffer()
        print()
        buffer.write_int(13)
        buffer.write_byte(b'\x1f\x1f\x1f')
        client.match.player1.connection.write(buffer.get_byte_array())
        client.match.player2.connection.write(buffer.get_byte_array())
        buffer.clear()

    async def handle_timeout(self, client: Client):
        client.match.timed_out = True
        
        self.send_timeout(client)
        
        if client == client.match.player1:
            next_client = client.match.player2
        else:
            next_client = client.match.player1
        
        self.send_empty_turn(next_client)
        print(f"{client.username} timed out on their turn!")

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
            client.connection.write(login.handle_reconnection(client, self.q_matches))

    def handle_avatar_update(self, data:list, client: Client):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        length = buffer.read_int()
        ava_code = bytes(buffer.read_bytes(length))
        self.accounts.update_avatar(client.username, ava_code)

    def handle_registration(self, data: list, client: Client):
        # Attempt registration and retrieve a response string to send back to the client
        registration_result = register.handle_register(bytes(data), client, self.accounts)
        
        # Send response string to client
        client.connection.write(registration_result)


    def process_match_stats(self, data: list, client: Client):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        names = [buffer.read_string() for i in range(3)]
        won = buffer.read_int()
        for name in names:
            path = self._stats_directory / f"{name}.dat"
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

    def handle_disconnected_player_update(self, client: Client, win: bool = False):
        player_info = ByteBuffer()
        player_info.write_bytes(login.get_player_info(self.accounts.get(client.username)))
        player_info.read_int()
        wins = player_info.read_int()
        losses = player_info.read_int()
        medals = player_info.read_int()
        mission_data = player_info.read_string()
        if win:
            wins += 1
        else:
            losses += 1
        #TODO Add streak handling
        
        print(f"Updating {client.username} to W: {wins} / L: {losses}")
        
        data = f"{wins}/{losses}/{medals}|{mission_data}"
        self.accounts.update_data(client.username, data)
        
        

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
        if start_package_response := qm_start_package.handle_start_package(bytes(data), client, self.q_matches):
            mID = start_package_response[0]
            p1_message = start_package_response[1]
            p2_message = start_package_response[2]
            self.q_matches.send_player1_message(mID, p1_message)
            self.q_matches.send_player2_message(mID, p2_message)
            
            first_player = client.match.player1 if client.match.player1_first else client.match.player2
            
            client.match.start_client_timer(first_player, self.handle_timeout)

    def handle_ranked_start_package(self, data: list, client: Client):
        if start_package_response := ranked_start_package.handle_start_package(bytes(data), client, self.r_matches):
            mID = start_package_response[0]
            p1_message = start_package_response[1]
            p2_message = start_package_response[2]
            self.r_matches.send_player1_message(mID, p1_message)
            self.r_matches.send_player2_message(mID, p2_message)
            
            first_player = client.match.player1 if client.match.player1_first else client.match.player2
            
            client.match.start_client_timer(first_player, self.handle_draft_timeout)
    
    

    def handle_surrender(self, data: list, client: Client):
        if client == client.match.player1:
            client.match.player2_won = True
            self.send_surrender_notification(client.match.player2, data)
        elif client == client.match.player2:
            client.match.player1_won = True
            self.send_surrender_notification(client.match.player1, data)

    def handle_draft_message(self, data: list, client: Client):
        
        in_buffer = ByteBuffer()
        in_buffer.write_bytes(data)
        in_buffer.read_int()
        character = in_buffer.read_string()
        
        out_buffer = ByteBuffer()
        out_buffer.write_int(11)
        out_buffer.write_string(character)
        out_buffer.write_byte(b'\x1f\x1f\x1f')
        
        
        if client == client.match.player1:
            client.match.player2.connection.write(out_buffer.get_byte_array())
            client.match.start_client_timer(client.match.player1, self.handle_draft_timeout)
        elif client == client.match.player2:
            client.match.player1.connection.write(out_buffer.get_byte_array())
            client.match.start_client_timer(client.match.player2, self.handle_draft_timeout)
            
        

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

    def send_empty_turn(self, client: Client):
        if client.match.timed_out:
            client.match.player1_turn = not client.match.player1_turn
            client.match.timed_out = False
            client.match.first_turn -= 1
            if client.match.first_turn < 0:
                client.match.first_turn = 0
            
            buffer = ByteBuffer()
            buffer.write_int(1)
            # timeout flag
            buffer.write_int(1)
            # ability message length            
            buffer.write_int(0)
            # execution order length
            buffer.write_int(0)
            for i in range(4):
                buffer.write_int(0)
            client.match.turn_history.append(buffer.get_byte_array()[8:])
            
            
            
            energy_pool = list()
            if not client.match.first_turn:
                min_roll = 0
                max_roll = 3
            else:
                min_roll = 5
                max_roll = 5
            for i in range(6):
                random_energy = random.randint(min_roll, max_roll)
                
                energy_pool.append(random_energy)
                buffer.write_int(random_energy)
            buffer.write_byte(b'\x1f\x1f\x1f')
            
            if client == client.match.player1:
                client.match.player1_energy_history.append(energy_pool)
                client.match.start_client_timer(client.match.player1, self.handle_timeout)
                client.match.player1.connection.write(buffer.get_byte_array())
                
            elif client == client.match.player2:
                client.match.player2_energy_history.append(energy_pool)
                client.match.start_client_timer(client.match.player2, self.handle_timeout)
                client.match.player2.connection.write(buffer.get_byte_array())
                
            else:
                pass #TODO: add custom error
            buffer.clear()
            

    def handle_match_communication(self, data: list, client: Client):
        
        if type(client.match) == RankedMatch:
            timeout = self.handle_draft_timeout
        else:
            timeout = self.handle_timeout
        
        print(f"Match communication received from {client.username}")
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        if not client.match.timed_out:
            client.match.message_received = True
            client.match.turn_history.append(data[8:])
            client.match.player1_turn = not client.match.player1_turn
            client.match.first_turn -= 1
            if client.match.first_turn < 0:
                client.match.first_turn = 0
            energy_pool = list()
            if not client.match.first_turn:
                min_roll = 0
                max_roll = 3
            else:
                min_roll = 5
                max_roll = 5
            for i in range(6):
                random_energy = random.randint(min_roll, max_roll)
                
                energy_pool.append(random_energy)
                buffer.write_int(random_energy)
            buffer.write_byte(b'\x1f\x1f\x1f')


            if client == client.match.player1:
                client.match.player2_energy_history.append(energy_pool)
                client.match.player2.connection.write(buffer.get_byte_array())
                client.match.start_client_timer(client.match.player2, timeout)
            elif client == client.match.player2:
                client.match.player1_energy_history.append(energy_pool)
                client.match.player1.connection.write(buffer.get_byte_array())
                client.match.start_client_timer(client.match.player1, timeout)
            else:
                pass #TODO: add custom error
            
            buffer.clear()

    def handle_match_ending(self, data: list, client: Client):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        client_won = buffer.read_int()
        buffer.clear()
        
        client.match.resolve_win_status(client, client_won)
        client.check_out()
        if client.match.over:
            if client.match.player1_disconnected:
                self.handle_disconnected_player_update(client.match.player1, client.match.player1_won)
            if client.match.player2_disconnected:
                self.handle_disconnected_player_update(client.match.player2, client.match.player2_won)
            if type(client.match) == QuickMatch:
                self.q_matches.end_match(client.match.get_match_id())
            elif type(client.match) == RankedMatch:
                self.r_matches.end_match(client.match.get_match_id())

    def handle_search_cancellation(self, data: list, client: Client):
        
        self.q_matches.end_open_match_by_player_name(client)
        self.r_matches.end_open_match_by_player_name(client)
        
