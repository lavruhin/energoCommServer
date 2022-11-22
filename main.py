import asyncio
import queue
import datetime
import os


HOST = "192.168.1.10"
PORT = 10001
PATH = "D:\\Work_Data\\EnergoCommData"

clients = dict()
points = \
    {b"!014017\r": [1, "Sta01"],
     b"!024017\r": [2, "Sta02"],
     b"!034017\r": [3, "Loco01"],
     b"!044017\r": [4, "Loco02"],
     b"ECHO\r": "Echo client"}
command_get_data = \
    {"Sta01": "#01\r",
     "Sta02": "#02\r",
     "Loco01": "#03\r",
     "Loco02": "#04\r"}
mirrors_queues = dict()


async def handle_connection(reader, writer):
    global clients
    adr = writer.get_extra_info("peername")
    print("Connected by", adr)
    timeout_cnt = 0
    point_number = 0
    while True:
        # Register a client in the list
        if adr not in clients: # and adr not in mirrors_queues:
            # Request to detect who is it
            for sync_data in ["$01M\r", "$02M\r", "$03M\r", "$04M\r"]:
                print(f"Send to {adr}: {sync_data}")
                try:
                    writer.write(sync_data.encode())
                    await writer.drain()
                except ConnectionError:
                    print(f"Client suddenly closed, cannot send")
                    break
                await asyncio.sleep(1)
            # Listen to an answer
            try:
                received_data = await asyncio.wait_for(reader.read(1024), timeout=5)
            except ConnectionError:
                print(f"Client suddenly closed while receiving from {adr}")
                break
            except asyncio.TimeoutError:
                print("Next attempt by timeout")
                continue
            print(f"Received from {adr}: {received_data}")
            # Answer from echo mirror
            if received_data == b'ECHO':
                mirrors_queues[adr] = queue.Queue(20)
            # Answer from measurer
            elif received_data in points:
                point_number = points[received_data][0]
                clients[adr] = points[received_data][1]
        elif adr in clients:
            sync_data = command_get_data[clients[adr]]
            try:
                print("Send request")
                writer.write(sync_data.encode())
                await writer.drain()
            except ConnectionError:
                print("Disconnect during sending")
                del clients[adr]
                break
            # Listen to an answer
            try:
                received_data = await asyncio.wait_for(reader.read(1024), timeout=10)
                try:
                    print(f"Received from {clients[adr]}: {received_data.decode()}")
                    # for key in mirrors_queues:
                    #     mirrors_queues[key].put(measures)
                    #     print(f"Put {measures} to mirror")
                except (UnicodeError, ValueError):
                    print('Value Error')
                dt = datetime.datetime.now()
                filename = f"{PATH}\\{point_number:02}_{dt.year:04}_{dt.month:02}_{dt.day:02}.csv"
                if not os.path.isfile(filename):
                    with open(filename, mode="w") as file:
                        file.write("Объект; Дата; Время; Напряжение; Ток-1; Ток-2; Широта; Долгота; Скорость\n")
                with open(filename, mode="a") as file:
                    file.write(received_data.decode())
                # Parse measured data
            except (ConnectionError, asyncio.TimeoutError):
                timeout_cnt += 1
            if timeout_cnt >= 2:
                print("Disconnect by timeout")
                del clients[adr]
                break
        if adr in mirrors_queues:
            try:
                while not mirrors_queues[adr].empty():
                    data = mirrors_queues[adr].get()
                    print(f"Get {data} from mirror")
                    writer.write(data.encode())
                    await writer.drain()
            except ConnectionError:
                print(f"Client suddenly closed, cannot send")
                break
    writer.close()
    print("Disconnected by", adr)


async def main(host, port):
    if not os.path.exists(PATH):
        try:
            os.mkdir(PATH)
        except OSError:
            print("Folder cannot be created")
            exit(-1)
    server = await asyncio.start_server(handle_connection, host, port)
    print(f"Start server...")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main(HOST, PORT))
