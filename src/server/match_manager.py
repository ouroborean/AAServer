from server.match import Match

class MatchManager():

    matches: dict = {}
    waiting_matches: list = []

    def __init__(self):
        pass

    def create_open_match(self, client, start_package):
        self.waiting_matches.append(Match(client, start_package))
        
    

    def close_match(self, client, start_package) -> str:
        match = self.waiting_matches[0]
        match.finish_forming_match(client, start_package)
        self.waiting_matches.clear()
        mID = match.get_match_id()
        self.matches[mID] = match
        return mID

manager = MatchManager()
    
    
