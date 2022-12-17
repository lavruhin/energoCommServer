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
current_data = dict()
vals = [[0, 0, 0], [0, 0, 0], [0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0]]


async def handle_connection(reader, writer):
    global clients
    adr = writer.get_extra_info("peername")
    print("Connected by", adr)
    timeout_cnt = 0
    point_number = 0
    tail = ""
    while True:
        # Register a client in the list
        if adr not in clients:
            # Request to detect who is it
            for sync_data in ["$01M\r", "$02M\r", "$03M\r", "$04M\r"]:
                print(f"Send to {adr}: {sync_data}")
                try:
                    writer.write(sync_data.encode())
                    await writer.drain()
                except (ConnectionError, OSError):
                    print(f"Client suddenly closed, cannot send")
                    break
                await asyncio.sleep(1)
            # Listen to an answer
            try:
                received_data = await asyncio.wait_for(reader.read(1024), timeout=5)
            except (ConnectionError, OSError):
                print(f"Client suddenly closed while receiving from {adr}")
                break
            except asyncio.TimeoutError:
                print("Next attempt by timeout")
                continue
            print(f"Received from {adr}: {received_data}")
            # Answer from measurer
            if received_data in points:
                point_number = points[received_data][0]
                clients[adr] = points[received_data][1]
        elif adr in clients:
            sync_data = command_get_data[clients[adr]]
            try:
                if clients[adr][0:3] == "Sta":
                    data_to_send = sync_data
                else:
                    data_to_send = sync_data[0:3] + \
                                   f" {vals[0][0]:1.0f} {vals[0][1]:1.2f} {vals[0][2]:1.2f}" + \
                                   f" {vals[1][0]:1.0f} {vals[1][1]:1.2f} {vals[1][2]:1.2f}" + \
                                   f" {vals[2][0]:1.0f} {vals[2][1]:1.2f} {vals[2][2]:1.2f}" + \
                                   f" {vals[2][3]:1.0f} {vals[2][4]:1.2f} {vals[2][5]:1.4f} {vals[2][6]:1.4f}" + \
                                   f" {vals[3][0]:1.0f} {vals[3][1]:1.2f} {vals[3][2]:1.2f}" + \
                                   f" {vals[3][3]:1.0f} {vals[3][4]:1.2f} {vals[3][5]:1.2f} {vals[3][6]:1.4f} \r"
                    print(data_to_send)
                writer.write(data_to_send.encode())
                await writer.drain()
            except (ConnectionError, OSError):
                print("Disconnect during sending")
                del clients[adr]
                break
            # Listen to an answer
            try:
                received_data = await asyncio.wait_for(reader.read(1024), timeout=10)
                received_msgs = received_data.split(b'\n')
                if tail != "":
                    received_msgs[0] = tail + received_msgs[0]
                    tail = ""
                if received_data[-1] != 13:
                    tail = received_msgs[-1]
                    received_msgs.pop(-1)
                dt = datetime.datetime.now()
                filename = f"{PATH}\\{point_number:02}_{dt.year:04}_{dt.month:02}_{dt.day:02}.csv"
                if not os.path.isfile(filename):
                    with open(filename, mode="w") as file:
                        file.write(
                            "Объект; Дата; Время; Напряжение; Ток-1; Ток-2; Широта; Долгота; Скорость; Расстояние\n")
                for message in received_msgs:
                    try:
                        message_str = message.decode()
                        message_vals = message_str.split(';')
                        print(f"Received from {clients[adr]}: {message_str}")
                        with open(filename, mode="a") as file:
                            file.write(message_str + '\r')
                        if clients[adr] == "Sta01":
                            point = 0
                        elif clients[adr] == "Sta02":
                            point = 1
                        elif clients[adr] == "Loco01":
                            point = 2
                        else:
                            point = 3
                        if point <= 1:
                            vals[point] = [float(message_vals[3]), float(message_vals[4]), float(message_vals[5])]
                        else:
                            vals[point] = [float(message_vals[3]), float(message_vals[4]), float(message_vals[5]),
                                           float(message_vals[8]), float(message_vals[9]), float(message_vals[6]),
                                           float(message_vals[7])]
                    except (UnicodeError, ValueError):
                        print('Value Error in received data')
            except (ConnectionError, asyncio.TimeoutError):
                timeout_cnt += 1
            if timeout_cnt >= 2:
                print("Disconnect by timeout")
                del clients[adr]
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
