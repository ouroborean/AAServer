import asyncio
import sys
from server.data_handler import Server
import logging

async def main():

    logging.basicConfig(level=logging.DEBUG,
                    format="%(levelname)s:%(relativeCreated)d:%(module)s:%(message)s")
    
    path = sys.argv[1]
    server = Server(path)

    
    echo_server = await asyncio.start_server(server.handle_echo, port=5692)
    async with echo_server:
        await echo_server.serve_forever()


asyncio.run(main())