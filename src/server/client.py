from typing import TYPE_CHECKING, Union
from server.player_status import PlayerStatus

if TYPE_CHECKING:
    from server.match import QuickMatch, RankedMatch


client_db = {}

class Client():
    
    match: Union["QuickMatch", "RankedMatch"]
    checked_out: bool
    status: PlayerStatus

    def __init__(self, client, address1, address2):
        self.connection = client
        self.match = None
        self.client_id = f"{address1}:{address2}"
        self.username = ""
        self.nonce = 0
        self.checked_out = False
        self.status = PlayerStatus.ONLINE

    def check_out(self):
        self.checked_out = True
        
    def reset(self):
        self.checked_out = False
        self.match = None
        if client_db[self.username] == PlayerStatus.DISCONNECTED:
            client_db[self.username] = PlayerStatus.OFFLINE
        
