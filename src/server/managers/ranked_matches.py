from server.match import RankedMatch
import logging

class RankedMatchManager():

    matches: dict[str, RankedMatch] = dict()
    waiting_matches: list[RankedMatch] = list()

    def __init__(self):
        self.matches = dict()
        self.waiting_matches = list()

    def create_open_match(self, client, start_package):
        logging.debug("Created new open ranked match!")
        self.waiting_matches.append(RankedMatch(client, start_package))
        
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

    
    
