from server import client
from server.client import Client, client_db
from server.player_status import PlayerStatus
import random

class Match():

    player1: Client
    player2: Client
    player1_start_package: list
    player2_start_package: list
    player1_energy: list
    player2_energy: list
    last_package: list
    match_id: list
    player1_turn: bool
    player1_first:bool
    first_turn: int
    player1_package: bool

    def __init__(self, player1: Client, start_package: list):
        self.player1 = player1
        self.player1_turn = True
        self.player1.match = self
        self.player1_package = False
        self.player1_energy = [0,0,0,0]
        self.player2_energy = [0,0,0,0]
        self.match_id = []
        self.last_package = []
        self.first_turn = 2
        self.match_id.append(player1.username)
        self.player1_start_package = start_package

    def finish_forming_match(self, player2: Client, start_package: list):
        self.player2 = player2
        self.player2.match = self
        self.match_id.append(player2.username)
        self.player2_start_package = start_package

        first_turn = random.randint(0,1)
        self.player1_first = not first_turn
        self.player1_turn = self.player1_first
        if self.player1_first:
            self.player1_energy = self.generate_first_player_energy(self.player1_energy)
            self.player2_energy = self.generate_second_player_energy(self.player2_energy)
        else:
            self.player2_energy = self.generate_first_player_energy(self.player2_energy)
            self.player1_energy = self.generate_second_player_energy(self.player1_energy)

    def generate_first_player_energy(self, energy) -> list:
        roll = random.randint(0,3)
        energy[roll] += 1
        return energy

    def generate_second_player_energy(self, energy) -> list:
        for i in range(3):
            roll = random.randint(0,3)
            energy[roll] += 1
        return energy

    def rejoin_match(self, player: Client):
        if player.username == self.player1.username:
            self.player1 = player
            player.match = self
            client_db[player.username] = PlayerStatus.ONLINE
        elif player.username == self.player2.username:
            self.player2 = player
            player.match = self
            client_db[player.username] = PlayerStatus.ONLINE


    def get_match_id(self):
        return self.match_id[0] + "/" + self.match_id[1]
