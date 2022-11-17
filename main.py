import asyncio
import queue
import time


clients = dict()
points = \
    {b"!014017\r": "Sta01",
     b"!024017\r": "Sta02",
     b"!034017\r": "Loco01",
     b"!044017\r": "Loco02",
     b"ECHO\r": "Echo client"}
command_get_data = \
    {"Sta01": "#01\r",
     "Sta02": "#02\r",
     "Loco01": "#03\r",
     "Loco02": "#04\r"}
mirrors_queues = dict()


async def handle_connection(reader, writer):
    global clients
    last_sync_time = time.time()
    adr = writer.get_extra_info("peername")
    print("Connected by", adr)
    while True:
        # Register a client in the list
        if adr not in clients and adr not in mirrors_queues:
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
                received_data = await reader.read(1024)
            except ConnectionError:
                print(f"Client suddenly closed while receiving from {adr}")
                break
            print(f"Received from {adr}: {received_data}")
            # Answer from echo mirror
            if received_data == b'ECHO':
                mirrors_queues[adr] = queue.Queue(20)
            # Answer from measurer
            elif received_data in points:
                clients[adr] = points[received_data]
                last_sync_time = time.time()
        if adr in clients:
            # Wait for sync period
            while time.time() - last_sync_time < SYNC_PERIOD - 0.1:
                await asyncio.sleep(0.2)
            last_sync_time = time.time() #last_sync_time + SYNC_PERIOD
            # Send sync to the client
            sync_data = command_get_data[clients[adr]]
            # print(f"Send to {adr}: {sync_data}")
            try:
                writer.write(sync_data.encode())
                await writer.drain()
            except ConnectionError:
                print("Client suddenly closed")
                del clients[adr]
                break
            # Listen to an answer
            try:
                received_data = await asyncio.wait_for(reader.read(1024), timeout=10)
            except ConnectionError:
                print("Client suddenly closed")
                del clients[adr]
                break
            except (asyncio.exceptions.CancelledError, TimeoutError):
                print("TIMEOUT!")
                del clients[adr]
                break
            # Parse measured data
            try:
                print(f"Received from {clients[adr]}: {received_data.decode()}")
                # value_u1 = float(received_data[1:8].decode())
                # value_u2 = float(received_data[8:15].decode())
                # value_i1 = float(received_data[15:22].decode())
                # value_i2 = float(received_data[22:29].decode())
                # measures = f"{clients[adr]}:  U1 = {value_u1}  U2 = {value_u2}  I1 = {value_i1}  I2 = {value_i2}"
                # rec_arr = received_data.decode().split(' ')
                # if len(rec_arr) == 6:
                #     gps_data = ""
                #     for item in rec_arr[1:7]:
                #         gps_data = gps_data + " " + item
                #     measures = gps_data + measures
                # print(measures)
                # for key in mirrors_queues:
                #     mirrors_queues[key].put(measures)
                #     print(f"Put {measures} to mirror")
            except (UnicodeError, ValueError):
                print('Value Error')
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

        # try:
        #     received_data = await reader.read(1024)
        # except ConnectionError:
        #     print(f"Client suddenly closed while receiving from {addr}")
        #     break
        # print(f"Received from {addr}: {received_data}")
        # if not received_data:
        #     break
        # # Process
        # if received_data == b"close":
        #     break

        # data = data.upper()
        # Send
        # print(f"Send: {data} to: {addr}")
        # try:
        #     writer.write(data)  # New
        #     await writer.drain()
        # except ConnectionError:
        #     print(f"Client suddenly closed, cannot send")
        #     break
    writer.close()
    print("Disconnected by", adr)


async def main(host, port):
    server = await asyncio.start_server(handle_connection, host, port)
    print(f"Start server...")
    async with server:
        await server.serve_forever()


HOST = "192.168.1.10"
PORT = 10001
SYNC_PERIOD = 2.0

if __name__ == "__main__":
    asyncio.run(main(HOST, PORT))


def parse(receivedString):
    if receivedStr[0:4] == b'@NTC':
        type = 'smart'
        return (type, parseSmart(receivedString))


def parseSmart(receivedString):
    head = receivedString[0:16]
    cmd = receivedString[16:20]
    if receivedString[16:20] == b'*>S:':
        imei = receivedString[20:35]
        answerBody = '*<S'.encode()
        return packAnswerSmart(head, answerBody)
    if receivedString[16:22] == b'*>FLEX':
        protocol = receivedString[22:23]
        protocol_version = receivedString[23:24]
        struct_version = receivedString[24:25]
        data_size = receivedString[25:26]
        if struct_version == b'\x0a':
            bitfield = receivedString[26:35]
        if struct_version == b'\x14':
            bitfield = receivedString[26:42]
        answerBody = '*<FLEX'.encode() + protocol + protocol_version + struct_version
        return packAnswerSmart(head, answerBody)
    return b'\x00'


def packAnswerSmart(head, answerBody):
    answerHead = head[0:4] + head[8:12] + head[4:8] + len(answerBody).to_bytes(2, 'little')
    checksumBody = 0
    for el in answerBody:
        checksumBody ^= el
    answerHead += checksumBody.to_bytes(1, 'little')
    checksumHead = 0
    for el in answerHead:
        checksumHead ^= el
    answerHead += checksumHead.to_bytes(1, 'little')
    return answerHead + answerBody

# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# server_address = ('192.168.1.11', 10001)
# print('Server {} starts, port {}'.format(*server_address))
# sock.bind(server_address)
# sock.listen(1)
#
# while True:
#     print('Waiting for connection...')
#     connection, client_address = sock.accept()
#     try:
#         print('Connected to:', client_address)
#         while True:
#             requestStr = '#01\r'
#             connection.sendall(requestStr.encode())
#             print('Send: ' + requestStr)
#             time.sleep(1)
#             receivedStr = connection.recv(1000)
#             print('Recv: ' + (receivedStr.decode()))
#
#
#             # receivedStr = connection.recv(1000)
#             # print(f'Received: {receivedStr.hex()}')
#             # print(f'Received: {receivedStr.decode("cp1251")}')
#             #
#             # (packetType, answerStr) = parse(receivedStr)
#             # if answerStr != b'\x00':
#             #     connection.sendall(answerStr)
#             #     print(packetType)
#             #     print(f'Send:     {answerStr.hex()}')
#             #     print(f'Send:     {answerStr.decode("cp1251")}')
#
#             #            print([data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7]])
#             #            if False:
#             #                print([data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9],
#             #                       data[10], data[11], data[12], data[13], data[14], data[15], data[16], data[17], data[18], data[19],
#             #                       data[20], data[21], data[22], data[23], data[24], data[25], data[26], data[27], data[28], data[29],
#             #                       data[30], data[31], data[32], data[33], data[34], data[35], data[36], data[37], data[38], data[39],
#             #                       data[40], data[41], data[42], data[43], data[44], data[45], data[46], data[47], data[48], data[49],
#             #                       data[50], data[51], data[52], data[43], data[54], data[55], data[56]])
#
#     finally:
#         connection.close()
