import asyncio
from server.byte_buffer import ByteBuffer
from server import data_handler
from server.client import Client, client_db
from server.match_manager import manager

async def handle_echo(reader, writer):
    client = Client(writer, writer.get_extra_info('peername')[0], writer.get_extra_info('peername')[1])
    buffer = ByteBuffer()
    while True:
        data = await reader.read(120000)
        if not data:
            break
        buffer.write_bytes(data)
        packet_id = buffer.read_int(False)
        data_handler.packets[packet_id](buffer.buff, client)
        buffer.clear()
    if client.username != "":
        client_db[client.username] = False
        print(f"Player {client.username} disconnected from server.")

        for match in manager.matches.values():
            if client == match.player1:
                data_handler.send_surrender_notification(match.player2)
                with open(f"accounts/{client.username}.dat") as f:
                    lines = f.readlines()
                    losses = int(lines[2])
                    lines[2] = str(losses + 1) + "\n"
    
                with open(f"accounts/{client.username}.dat", "w") as f:
                    for line in lines:
                        f.writelines(line)
            elif client == match.player2:
                data_handler.send_surrender_notification(match.player1)
                with open(f"accounts/{client.username}.dat") as f:
                    lines = f.readlines()
                    losses = int(lines[2])
                    lines[2] = str(losses + 1) + "\n"
    
                with open(f"accounts/{client.username}.dat", "w") as f:
                    for line in lines:
                        f.writelines(line)
        for match in manager.waiting_matches:
            if match.player1 == client:
                manager.waiting_matches.clear()



async def main():
    server = await asyncio.start_server(handle_echo, host="10.182.0.2", port=5692)
    async with server:
        await server.serve_forever()


asyncio.run(main())