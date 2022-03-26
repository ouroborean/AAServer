import asyncio
import sys
from server.data_handler import Server



async def main():

    path = sys.argv[1]
    server = Server(path)


    echo_server = await asyncio.start_server(server.handle_echo, port=5692)
    async with echo_server:
        await echo_server.serve_forever()


asyncio.run(main())