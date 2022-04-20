import asyncio
from typing import TYPE_CHECKING, Callable
from server.client import Client, client_db
from server.player_status import PlayerStatus
from server.turn_timer import TurnTimer
import functools
import random
if TYPE_CHECKING:
    from server.handlers.start_package import StartPackage

MATCH_TURN_TIME = 90

class Match():

    player1: Client
    player2: Client
    player1_start_package: 'StartPackage'
    player2_start_package: 'StartPackage'
    player1_energy_history: list
    player2_energy_history: list
    last_package: list
    match_id: list
    player1_turn: bool
    player1_first:bool
    first_turn: int
    turn_history: list
    turn_timer: TurnTimer
    message_received: bool
    timed_out: bool

    def __init__(self, player1: Client, start_package: 'StartPackage'):
        self.player1 = player1
        self.player2 = None
        self.player1_turn = True
        self.player1.match = self
        self.player1_energy_history = list()
        self.player2_energy_history = list()
        self.match_id = []
        self.last_package = []
        self.first_turn = 2
        self.match_id.append(player1.username)
        self.player1_start_package = start_package
        self.turn_history = list()
        self.message_received = False
        self.timed_out = False
        self.turn_timer = None
        
    def start_client_timer(self, client: Client, callback: Callable):
        if self.turn_timer:
            self.turn_timer.cancel()
        timer_callback = functools.partial(callback, client)
        self.turn_timer = TurnTimer(MATCH_TURN_TIME, timer_callback)
        
        

    def finish_forming_match(self, player2: Client, start_package: 'StartPackage'):
        self.player2 = player2
        self.player2.match = self
        self.match_id.append(player2.username)
        self.player2_start_package = start_package

        first_turn = random.randint(0,1)
        self.player1_first = not first_turn
        self.player1_turn = self.player1_first
        self.player1_energy_history.append(self.generate_starting_energy())
        self.player2_energy_history.append(self.generate_starting_energy())

    def generate_starting_energy(self):
        return [random.randint(0, 3) for i in range(6)]

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
        if len(self.match_id) == 2:
            return self.match_id[0] + "/" + self.match_id[1]
        else:
            return self.match_id[0]
