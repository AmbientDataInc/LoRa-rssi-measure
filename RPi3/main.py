# sf, bwを変えながら移動端末から受信する
#
# LoRaモジュールから1行読み、rssi、panid、srcid、msgに分解
# さらにmsgが'latlng=(lat,lng)'という形式なので、'(lat,lng)'部分をTupleに変換
# rssiを保存し、Ambientに送信
#
#

import lora
import ast
import time
import struct
import sys
import ambient

# (bw, sf, timeout)
mode = [
    (3, 12, 5), (3, 11, 5), (3, 10, 4), (3, 9, 3), (3, 8, 2), (3, 7, 2),
    (4, 12, 5), (4, 11, 4), (4, 10, 3), (4, 9, 3), (4, 8, 2), (4, 7, 2),
    (5, 12, 4), (5, 11, 3), (5, 10, 2), (5, 9, 2), (5, 8, 2), (5, 7, 2),
    (6, 12, 3), (6, 11, 3), (6, 10, 2), (6, 9, 2), (6, 8, 2), (6, 7, 2)
]

channelId1 = チャネルID1
writeKey1 = 'ライトキー1'
channelId2 = チャネルID2
writeKey2 = 'ライトキー2'
channelId3 = チャネルID3
writeKey3 = 'ライトキー3'
channelId4 = チャネルID4
writeKey4 = 'ライトキー4'

am1 = ambient.Ambient(channelId1, writeKey1)
am2 = ambient.Ambient(channelId2, writeKey2)
am3 = ambient.Ambient(channelId3, writeKey3)
am4 = ambient.Ambient(channelId4, writeKey4)

lr = lora.LoRa()

def printable(l):
    x = struct.unpack(str(len(l)) + 'b', l)
    y = ''
    for i in range(len(x)):
        if x[i] >= 0:
            y = y + chr(x[i])
    return y

def sendcmd(cmd):
    # print(cmd)
    lr.write(cmd)
    t = time.time()
    while (True):
        if (time.time() - t) > 5:
            print('panic: %s' % cmd)
            exit()
        line = lr.readline()
        if 'OK' in printable(line):
            # print(line)
            return True
        elif 'NG' in printable(line):
            # print(line)
            return False

def setMode(bw, sf):
    lr.write('config\r\n')
    lr.s.flush()
    time.sleep(0.2)
    lr.reset()
    time.sleep(1.5)

    line = lr.readline()
    while not ('Mode' in printable(line)):
        line = lr.readline()
        if len(line) > 0:
            print(line)

    sendcmd('2\r\n')
    sendcmd('bw %d\r\n' % bw)
    sendcmd('sf %d\r\n' % sf)
    sendcmd('q 2\r\n')
    sendcmd('w\r\n')

    lr.reset()
    print('LoRa module set to new mode')
    time.sleep(1)
    sys.stdout.flush()

while (True):
    rssi = [None] * len(mode)
    latlng = ()
    for i in range(len(mode)):
        print('setMode(bw: %d, sf: %d)' % (mode[i][0], mode[i][1]))
        setMode(mode[i][0], mode[i][1])

        t = None if i == 0 else mode[i][2]
        timeout = False
        start = time.time()
        while (True):
            while (True):
                line = lr.readline(t)
                # print(line)
                # sys.stdout.flush()
                if len(line) == 0: # TIMEOUT
                    timeout = True
                    break
                if len(line) >= 14: # 'rssi(4bytes),pan id(4bytes),src id(4bytes),\r\n'で14バイト
                    break
            if timeout == True:
                rssi[i] = None
                print('TIMEOUT')
                break;
            data = lr.parse(line)  # 'rssi(4bytes),pan id(4bytes),src id(4bytes),laglng=(12バイト,12バイト)\r\n', ペイロード34バイト
            print(data)
            if 'loc=' in data[3]:
                loc = ast.literal_eval(data[3].split('=')[1])
                rssi[i] = data[0]
                latlng = loc
                s = mode[i][2] - (time.time() - start)
                # print('sleep: ' + str(s))
                if i != 0 and s > 0:
                    time.sleep(s)
                break

    print(rssi)
    print(latlng)
    sys.stdout.flush()

    am1.send({'d1': rssi[5], 'd2': rssi[4], 'd3': rssi[3], 'd4': rssi[2], 'd5': rssi[1], 'd6': rssi[0], 'lat': latlng[0], 'lng': latlng[1]})
    am2.send({'d1': rssi[11], 'd2': rssi[10], 'd3': rssi[9], 'd4': rssi[8], 'd5': rssi[7], 'd6': rssi[6], 'lat': latlng[0], 'lng': latlng[1]})
    am3.send({'d1': rssi[17], 'd2': rssi[16], 'd3': rssi[15], 'd4': rssi[14], 'd5': rssi[13], 'd6': rssi[12], 'lat': latlng[0], 'lng': latlng[1]})
    am4.send({'d1': rssi[23], 'd2': rssi[22], 'd3': rssi[21], 'd4': rssi[20], 'd5': rssi[19], 'd6': rssi[18], 'lat': latlng[0], 'lng': latlng[1]})
