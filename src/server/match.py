import asyncio
from typing import TYPE_CHECKING, Callable
from server.client import Client, client_db
from server.player_status import PlayerStatus
from server.turn_timer import TurnTimer
import functools
import random
import time
import logging
if TYPE_CHECKING:
    from server.handlers.qm_start_package import QMStartPackage
    from server.handlers.ranked_start_package import RankedStartPackage

MATCH_TURN_TIME = 90

class QuickMatch():

    player1: Client
    player2: Client
    player1_start_package: 'QMStartPackage'
    player2_start_package: 'QMStartPackage'
    player1_energy_history: list
    player2_energy_history: list
    player1_random_seeds: list
    player2_random_seeds: list
    last_package: list
    match_id: list
    player1_turn: bool
    player1_first:bool
    first_turn: int
    turn_history: list
    turn_timer: TurnTimer
    message_received: bool
    timed_out: bool
    random_seed: int
    player1_won: bool
    player2_won: bool

    def __init__(self, player1: Client, start_package: 'QMStartPackage'):
        self.player1 = player1
        self.player2 = None
        self.player1_turn = True
        self.player1.match = self
        self.player1_energy_history = list()
        self.player2_energy_history = list()
        self.player1_random_seeds = list()
        self.player2_random_seeds = list()
        self.player1_won = False
        self.player2_won = False
        self.match_id = []
        self.last_package = []
        self.first_turn = 2
        self.match_id.append(player1.username)
        self.player1_start_package = start_package
        self.turn_history = list()
        self.message_received = False
        self.timed_out = False
        self.turn_timer = None
        self.player1_first = False
        
    @property
    def over(self) -> bool:
        
        player_1_finished = (self.player1.checked_out or client_db[self.player1.username] == PlayerStatus.DISCONNECTED or client_db[self.player1.username] == PlayerStatus.OFFLINE)
        player_2_finished = (self.player2.checked_out or client_db[self.player2.username] == PlayerStatus.DISCONNECTED or client_db[self.player2.username] == PlayerStatus.OFFLINE)
        
        return (player_1_finished and player_2_finished)
    
    @property
    def player1_disconnected(self) -> bool:
        return client_db[self.player1.username] == PlayerStatus.DISCONNECTED
    
    @property
    def player2_disconnected(self) -> bool:
        return client_db[self.player2.username] == PlayerStatus.DISCONNECTED
    
    def resolve_win_status(self, client: Client, won: bool):
        if client == self.player1:
            self.player1_won = won
            self.player2_won = not won
        else:
            self.player2_won = won
            self.player1_won = not won
    
    def end(self):
        self.player1.reset()
        self.player2.reset()
        self.turn_timer.cancel()
        for k, v in client_db.items():
            print(f"{k}: {v.name}")
        
    def start_client_timer(self, client: Client, callback: Callable):
        if self.turn_timer:
            self.turn_timer.cancel()
        timer_callback = functools.partial(callback, client)
        self.turn_timer = TurnTimer(MATCH_TURN_TIME, timer_callback)
        
        

    def finish_forming_match(self, player2: Client, start_package: 'QMStartPackage'):
        self.player2 = player2
        self.player2.match = self
        self.match_id.append(player2.username)
        self.player2_start_package = start_package
        self.random_seed = int(time.time())
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
            logging.debug("%s rejoined the match!", player.username)
            logging.debug("Match player-states: Player 1 - %s | Player 2 - %s", self.player1.username, self.player2.username)
        elif player.username == self.player2.username:
            self.player2 = player
            player.match = self
            client_db[player.username] = PlayerStatus.ONLINE
            logging.debug("%s rejoined the match!", player.username)
            logging.debug("Match player-states: Player 1 - %s | Player 2 - %s", self.player1.username, self.player2.username)


    def get_match_id(self):
        if len(self.match_id) == 2:
            return self.match_id[0] + "/" + self.match_id[1]
        else:
            return self.match_id[0]
        
class RankedMatch():

    player1: Client
    player2: Client
    player1_start_package: 'RankedStartPackage'
    player2_start_package: 'RankedStartPackage'
    player1_characters: list
    player2_characters: list
    player1_energy_history: list
    player2_energy_history: list
    player1_random_seeds: list
    player2_random_seeds: list
    last_package: list
    match_id: list
    player1_turn: bool
    player1_first:bool
    first_turn: int
    turn_history: list
    turn_timer: TurnTimer
    message_received: bool
    timed_out: bool
    random_seed: int
    player1_won: bool
    player2_won: bool

    def __init__(self, player1: Client, start_package: 'RankedStartPackage'):
        self.player1 = player1
        self.player2 = None
        self.player1_turn = True
        self.player1.match = self
        self.player1_energy_history = list()
        self.player2_energy_history = list()
        self.player1_random_seeds = list()
        self.player2_random_seeds = list()
        self.player1_characters = list()
        self.player2_characters = list()
        self.player1_won = False
        self.player2_won = False
        self.match_id = []
        self.last_package = []
        self.first_turn = 2
        self.match_id.append(player1.username)
        self.player1_start_package = start_package
        self.turn_history = list()
        self.message_received = False
        self.timed_out = False
        self.turn_timer = None
        self.player1_first = False
        
    @property
    def over(self) -> bool:
        
        player_1_finished = (self.player1.checked_out or client_db[self.player1.username] == PlayerStatus.DISCONNECTED or client_db[self.player1.username] == PlayerStatus.OFFLINE)
        player_2_finished = (self.player2.checked_out or client_db[self.player2.username] == PlayerStatus.DISCONNECTED or client_db[self.player2.username] == PlayerStatus.OFFLINE)
        
        return (player_1_finished and player_2_finished)
    
    @property
    def player1_disconnected(self) -> bool:
        return client_db[self.player1.username] == PlayerStatus.DISCONNECTED
    
    @property
    def player2_disconnected(self) -> bool:
        return client_db[self.player2.username] == PlayerStatus.DISCONNECTED
    
    def resolve_win_status(self, client: Client, won: bool):
        if client == self.player1:
            self.player1_won = won
            self.player2_won = not won
        else:
            self.player2_won = won
            self.player1_won = not won
    
    def end(self):
        self.player1.reset()
        self.player2.reset()
        self.turn_timer.cancel()
        for k, v in client_db.items():
            print(f"{k}: {v.name}")
        
    def start_client_timer(self, client: Client, callback: Callable):
        if self.turn_timer:
            self.turn_timer.cancel()
        timer_callback = functools.partial(callback, client)
        self.turn_timer = TurnTimer(MATCH_TURN_TIME, timer_callback)
        
        

    def finish_forming_match(self, player2: Client, start_package: 'RankedStartPackage'):
        self.player2 = player2
        self.player2.match = self
        self.match_id.append(player2.username)
        self.player2_start_package = start_package
        self.random_seed = int(time.time())
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
            logging.debug("%s rejoined the match!", player.username)
            logging.debug("Match player-states: Player 1 - %s | Player 2 - %s", self.player1.username, self.player2.username)
        elif player.username == self.player2.username:
            self.player2 = player
            player.match = self
            client_db[player.username] = PlayerStatus.ONLINE
            logging.debug("%s rejoined the match!", player.username)
            logging.debug("Match player-states: Player 1 - %s | Player 2 - %s", self.player1.username, self.player2.username)


    def get_match_id(self):
        if len(self.match_id) == 2:
            return self.match_id[0] + "/" + self.match_id[1]
        else:
            return self.match_id[0]
