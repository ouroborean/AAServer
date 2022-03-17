import asyncio
from server.byte_buffer import ByteBuffer
from server import data_handler
from server.client import Client, client_db
from server.match_manager import manager
from server.player_status import PlayerStatus

async def handle_echo(reader, writer):
    print("Client connected!")
    client = Client(writer, writer.get_extra_info('peername')[0], writer.get_extra_info('peername')[1])
    buffer = ByteBuffer()
    while True:
        try:
            data = await reader.readuntil(b'\x1f\x1f\x1f')
        except asyncio.exceptions.IncompleteReadError:
            break
        if not data:
            break
        buffer.write_bytes(data[:-3])
        print(f"Package received of length {len(data)}")
        packet_id = buffer.read_int(False)
        data_handler.packets[packet_id](buffer.buff, client)
        buffer.clear()
    if client.username != "":
        print(f"Player {client.username} disconnected from server.")
        if client.match:
            if client == client.match.player1 and client.match.get_match_id() in manager.matches:
                if client_db[client.match.player2.username] == PlayerStatus.DISCONNECTED:
                    data_handler.add_a_loss(client)
                    data_handler.add_a_loss(client.match.player2)
                    client_db[client.match.player2.username] = PlayerStatus.OFFLINE
                    client_db[client.username] = PlayerStatus.OFFLINE
                    data_handler.handle_match_ending([], client)
                else:
                    client_db[client.username] = PlayerStatus.DISCONNECTED
            elif client.match.player2 and client == client.match.player2 and client.match.get_match_id() in manager.matches:
                if client_db[client.match.player1.username] == PlayerStatus.DISCONNECTED:
                    data_handler.add_a_loss(client)
                    data_handler.add_a_loss(client.match.player1)
                    client_db[client.match.player1.username] = PlayerStatus.OFFLINE
                    client_db[client.username] = PlayerStatus.OFFLINE
                    data_handler.handle_match_ending([], client)
                else:
                    client_db[client.username] = PlayerStatus.DISCONNECTED
            else: 
                client_db[client.username] = PlayerStatus.OFFLINE
        else:
            client_db.pop(client.username)
        for match in manager.waiting_matches:
            if match.player1 == client:
                manager.waiting_matches.clear()



async def main():
    server = await asyncio.start_server(handle_echo, port=5692)
    async with server:
        await server.serve_forever()


asyncio.run(main())