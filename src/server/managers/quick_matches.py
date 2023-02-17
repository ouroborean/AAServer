from server.match import QuickMatch
import logging

class QuickMatchManager():

    matches: dict[str, QuickMatch] = dict()
    waiting_matches: list[QuickMatch] = list()

    def __init__(self):
        self.matches = dict()
        self.waiting_matches = list()

    def create_open_match(self, client, start_package):
        logging.debug("Created new open quick match!")
        self.waiting_matches.append(QuickMatch(client, start_package))
    
    def end_open_match_by_player_name(self, client):
        for match in self.waiting_matches:
            if match.player1.username == client.username:
                self.waiting_matches.remove(match)
    
    def send_player1_message(self, matchID: str, message: list[bytes]):
        self.matches[matchID].player1.connection.write(message)

    def send_player2_message(self, matchID: str, message: list[bytes]):
        self.matches[matchID].player2.connection.write(message)

    def clear_matches(self):
        self.waiting_matches.clear()

    def end_match(self, matchID: str):
        self.matches[matchID].end()
        self.matches.pop(matchID)

    def match_exists(self, matchID: str) -> bool:
        return matchID in self.matches

    def close_match(self, client, start_package) -> str:
        match = self.waiting_matches[0]
        match.finish_forming_match(client, start_package)
        self.waiting_matches.clear()
        mID = match.get_match_id()
        self.matches[mID] = match
        return mID

    
    
