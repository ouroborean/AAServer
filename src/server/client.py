

client_db = {}

class Client():
    
    def __init__(self, client, address1, address2):
        self.connection = client
        self.client_id = f"{address1}:{address2}"
        self.username = ""
