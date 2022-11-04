import socket
import sys
import time


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


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('192.168.1.11', 10001)
print('Server {} starts, port {}'.format(*server_address))
sock.bind(server_address)
sock.listen(1)

while True:
    print('Waiting for connection...')
    connection, client_address = sock.accept()
    try:
        print('Connected to:', client_address)
        while True:
            #           data = connection.recv(16)
            #           print(f'Received: {data.decode()}')
            #           if data:
            #               print('Processing...')
            #               data = data.upper()
            #               print('Request.')
            #               connection.sendall(data)
            #           else:
            #               print('Data message is empty from:', client_address)
            #               break
            data = "#01\r"
            print(data)
            # connection.sendall(data.encode())
            time.sleep(1)
            receivedStr = connection.recv(1000)
            print(f'Received: {receivedStr.hex()}')
            print(f'Received: {receivedStr.decode("cp1251")}')

            (packetType, answerStr) = parse(receivedStr)
            if answerStr != b'\x00':
                connection.sendall(answerStr)
                print(packetType)
                print(f'Send:     {answerStr.hex()}')
                print(f'Send:     {answerStr.decode("cp1251")}')

            #            print([data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7]])
            #            if False:
            #                print([data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9],
            #                       data[10], data[11], data[12], data[13], data[14], data[15], data[16], data[17], data[18], data[19],
            #                       data[20], data[21], data[22], data[23], data[24], data[25], data[26], data[27], data[28], data[29],
            #                       data[30], data[31], data[32], data[33], data[34], data[35], data[36], data[37], data[38], data[39],
            #                       data[40], data[41], data[42], data[43], data[44], data[45], data[46], data[47], data[48], data[49],
            #                       data[50], data[51], data[52], data[43], data[54], data[55], data[56]])
            #print(f'Received: {data.hex()}')
            #print(f'Received: {data.decode()}')
            #data = data[0:4] + data[8:12] + data[4:8] + b'\x03\x00' + b'\x45\x5e\x2a\x3c\x53'
            #print(f'Send:     {data.hex()}')
            #print(f'Send:     {data.decode()}')
            #connection.sendall(data)

    finally:
        connection.close()
