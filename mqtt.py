# https://stackoverflow.com/questions/7088672/pyaudio-working-but-spits-out-error-messages-each-time
from ctypes import *

# From alsa-lib Git 3fd4ab9be0db7c7430ebd258f2717a976381715d
# $ grep -rn snd_lib_error_handler_t
# include/error.h:59:typedef void (*snd_lib_error_handler_t)(const char *file, int line, const char *function, int err, const char *fmt, ...) /* __attribute__ ((format (printf, 5, 6))) */;
# Define our error handler type
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)


def py_error_handler(filename, line, function, err, fmt):
    pass


c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

asound = cdll.LoadLibrary('libasound.so')
# Set error handler
asound.snd_lib_error_set_handler(c_error_handler)

import subprocess
import paho.mqtt.client as mqtt
import json
import datetime
import calendar
import time

import pyaudio
import math
import struct
import wave
import sys

from kkbox_partner_sdk.auth_flow import KKBOXOAuth

CLIENT_ID = 'cea7cb81a731b46caeb9b8c0e25abd22'
CLIENT_SECRET = '6317f7914dcc9e1fb50d01f744b3f1fb'

auth = KKBOXOAuth(CLIENT_ID, CLIENT_SECRET)
token = auth.fetch_access_token_by_client_credentials()

from kkbox_partner_sdk.api import KKBOXAPI

kkboxapi = KKBOXAPI(token)
track_id = 'KmtpBrC4R1boMEdm1Q'
artist = kkboxapi.track_fetcher.fetch_track(track_id)
# print(artist)

# 遠端連線相關的定義
hostname = 'ibobby.ai.hinet.net'
port = 8883
venderId = 'compal'
deviceId = 'compal0x001'
Token = 'd0c451e67005ff99b860d54ef99e5428'

req = 'ai/speaker/{0}/{1}/req'.format(venderId, deviceId)
rsp = 'ai/speaker/{0}/{1}/rsp'.format(venderId, deviceId)
asr = 'ai/speaker/{0}/{1}/asr'.format(venderId, deviceId)
asr_debug = 'ai/speaker/{0}/{1}/asr_debug'.format(venderId, deviceId)

# 聲音相關的定義
# Assuming Energy threshold upper than 30 dB
Threshold = 80
SHORT_NORMALIZE = (1.0 / 32768.0)
chunk = 2400
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
swidth = 2
Max_Seconds = 3

TimeoutSignal = int((RATE / chunk * Max_Seconds) + 2)
Time = 0
silence = True


def increase():
    file = open('record.txt', 'r', encoding='utf-8')
    index = int(file.read())
    index += 1
    file.close()

    file = open('record.txt', 'w+', encoding='utf-8')
    file.write(str(index))
    file.close()
    return index


def getLocalTime():
    d = datetime.datetime.utcnow()
    ts = calendar.timegm(d.timetuple())
    localTime = datetime.datetime.fromtimestamp(ts).replace(microsecond=d.microsecond)
    return localTime


def getUTC():
    localTime = getLocalTime()
    utc = datetime.datetime.strftime(localTime, '%Y-%m-%dT%H:%M:%SZ')
    return utc


def getReqId():
    now = getLocalTime()
    index = increase()
    # reqId = 'EID{0}'.format(time.mktime(now.timetuple()) + 1e-6 * now.microsecond)
    reqId = 'EID{0}{1:0>2d}{2:0>2d}{3:0>2d}{4:0>2d}{5:0>5d}'.format(now.year, now.month, now.day, now.hour, now.minute,
                                                                    index)
    return reqId


def register():
    action = 'RegisterReq'
    time = getUTC()
    requestID = getReqId()
    json_payload = {
        'Action': action,
        'Time': time,
        'RequestID': requestID,
        'Version': '1.1'
    }
    payload = json.dumps(json_payload, sort_keys=True, ensure_ascii=False)
    return payload


def serviceInvoke(text):
    json_payload = {
        'Action': 'InvokeReq',
        'Time': getUTC(),
        'RequestID': getReqId(),
        'Text': text
    }
    payload = json.dumps(json_payload, sort_keys=True, ensure_ascii=False)
    print('我的問題是:' + json_payload.get('Text') + ', 時間:' + json_payload.get('Time') + ', 請求:' + json_payload.get(
        'RequestID'))
    return payload


def on_connect(client, userdata, flag, rc):
    print("連線結果:" + ('成功' if rc == 0 else '失敗'))
    client.subscribe(rsp)
    client.subscribe(asr_debug)
    # testServer()


def testServer():
    text = '今天新北市天氣如何'
    text = '今天有那些行程'
    text = '請問張惠妹是誰'
    text = '今天仁寶的股價是多少'
    text = '我要聽張惠妹的姊妹'
    client.publish(req, serviceInvoke(text))


def on_disconnect(client, userdata, rc):
    print("發生斷線")


# 處理遠端回傳的訊息
def on_message(client, userdata, msg):
    # print(msg.topic + ", " + str(msg.payload))
    payload = json.loads(msg.payload.decode('utf-8'))

    end = False
    flag = False

    if msg.topic == asr_debug:
        if 'Text' in payload:
            print("遠端收到使用者說了:" + payload.get('Text'))

    elif msg.topic == rsp:
        end = True
        if 'Commands' in payload:
            for ele in payload['Commands']:
                # print(ele)
                myType = ele.get('Type', 0)
                if myType == '01':
                    content = ele.get('Content', 0)
                    if content != 0 and not flag:
                        flag = True
                        print("回應的文字:" + content)

                    tUrl = ele.get('tUrl', 0)
                    print("說話中:" + tUrl)
                    subprocess.run(['ffplay', '-nodisp', '-autoexit', tUrl])
                    # result = subprocess.run(['ffplay', '-autoexit', tUrl], stdout=subprocess.PIPE)
                    # print(result.stdout)

                elif myType == '02':
                    content = ele.get('Content', 0)
                    if content != 0:
                        print("歌曲資訊:" + content)

                    # url = 'https://widget.kkbox.com/v1/?id=4kxvr3wPWkaL9_y3o_&type=song&terr=TW&lang=TC&autoplay=true&loop=true'
                    # result = subprocess.Popen(['chromium-browser', url], stdout=subprocess.PIPE)
                    # print(result.stdout)
                    tickets = kkboxapi.ticket_fetcher.fetch_media_provision(content)
                    # print(song)
                    tUrl = tickets['url']
                    subprocess.run(['ffplay', '-nodisp', '-autoexit', tUrl])

                elif myType == '04':
                    content = ele.get('Content', 0)
                    if content != 0:
                        print("回應的文字:" + content)

                else:
                    print('沒有登記過的類型')
                    print(ele)

            else:
                print('無法處理的主題')
                print(payload)

        if end:
            sys.exit()


# 以上是訊息處理的程式
# 底下是錄音相關的程式


def GetStream(chunk):
    return stream.read(chunk)


def rms(frame):
    count = len(frame) / swidth
    format = "%dh" % (count)
    shorts = struct.unpack(format, frame)

    sum_squares = 0.0
    for sample in shorts:
        n = sample * SHORT_NORMALIZE
        sum_squares += n * n

    rms = math.pow(sum_squares / count, 0.5);
    return rms * 1000


def WriteSpeech(WriteData):
    stream.stop_stream()
    stream.close()
    p.terminate()

    FileNameTmp = 'REC/rec{0}.wav'.format(getLocalTime())
    wf = wave.open(FileNameTmp, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(WriteData))
    wf.close()


def KeepRecord(TimeoutSignal, LastBlock):
    samples = []
    samples.append(LastBlock)
    for i in range(0, TimeoutSignal):
        try:
            data = GetStream(chunk)
        except:
            continue
        samples.append(data)

        payload = bytearray(b'\x01')
        payload.extend(data)
        client.publish(asr, bytes(payload))
        time.sleep(0.05)

    client.publish(asr, b'\x02')
    print("錄音結束")

    # print("寫入音檔完成")
    WriteSpeech(samples)


client = mqtt.Client()
client.username_pw_set(Token, Token)
client.tls_set('ROOTeCA_64.crt')
# client.tls_set_context(context=ssl.create_default_context())

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

client.connect("ibobby.ai.hinet.net", 8883)
# client.publish(req, register())

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                output=True,
                frames_per_buffer=chunk)

try:
    while True:
        client.loop(.1)

        if silence:
            try:
                input = GetStream(chunk)
            except:
                continue
            rms_value = int(rms(input))
            # print(rms_value)
            if (rms_value > Threshold):
                silence = False
                print('啟動音量:{0}'.format(rms_value))
                LastBlock = input
                print("開始錄音")
                client.publish(asr, b'\x00')
                KeepRecord(TimeoutSignal, LastBlock)

            Time = Time + 1
            if (Time > TimeoutSignal):
                Time = 0
                # print("時間範圍內沒有偵測到聲音")

except KeyboardInterrupt:
    print('鍵盤中斷')
