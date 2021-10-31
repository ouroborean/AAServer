from server.client import Client

class Match():

    player1: Client
    player2: Client
    player1_start_package: list
    player2_start_package: list
    match_id: list

    def __init__(self, player1: Client, start_package: list):
        self.player1 = player1
        self.player1.match = self
        self.match_id = []
        self.match_id.append(player1.client_id)
        self.player1_start_package = start_package

    def finish_forming_match(self, player2: Client, start_package: list):
        self.player2 = player2
        self.player2.match = self
        self.match_id.append(player2.client_id)
        self.player2_start_package = start_package

    def get_match_id(self):
        return self.match_id[0] + "/" + self.match_id[1]
