from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.match import Match


client_db = {}

class Client():
    
    match: "Match"

    def __init__(self, client, address1, address2):
        self.connection = client
        self.match = None
        self.client_id = f"{address1}:{address2}"
        self.username = ""
        self.nonce = 0
