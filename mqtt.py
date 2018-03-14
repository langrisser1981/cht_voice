import paho.mqtt.client as mqtt
import json
import datetime
import calendar
import time
import vlc

import pyaudio
import math
import struct
import wave

Instance = vlc.Instance()
player = Instance.media_player_new()
state = 0

hostname = 'ibobby.ai.hinet.net'
port = 8883
venderId = 'compal'
deviceId = 'compal0x001'
Token = 'd0c451e67005ff99b860d54ef99e5428'

req = 'ai/speaker/{0}/{1}/req'.format(venderId, deviceId)
rsp = 'ai/speaker/{0}/{1}/rsp'.format(venderId, deviceId)
asr = 'ai/speaker/{0}/{1}/asr'.format(venderId, deviceId)
asr_debug = 'ai/speaker/{0}/{1}/asr_debug'.format(venderId, deviceId)


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
    action = 'InvokeReq'
    time = getUTC()
    requestID = getReqId()
    json_payload = {
        'Action': action,
        'Time': time,
        'RequestID': requestID,
        'Text': text
    }
    payload = json.dumps(json_payload, sort_keys=True, ensure_ascii=False)
    print('我的問題是:' + text + ', 時間:' + time + ', 請求:' + requestID)
    return payload


def on_connect(client, userdata, flag, rc):
    print("連線結果:" + str(rc))

    client.subscribe(rsp)
    client.subscribe(asr_debug)
    testServer()


def testServer():
    text = '我要聽歌'
    text = '今天有那些行程'
    text = '今天新北市天氣如何'
    text = '請問張惠妹是誰'
    text = '今天仁寶的股價是多少'
    client.publish(req, serviceInvoke(text))


def on_disconnect(client, userdata, rc):
    print("斷線:" + str(rc))


def on_message(client, userdata, msg):
    # print(msg.topic+", "+str(msg.payload))
    payload = json.loads(msg.payload.decode('utf-8'))
    Action = payload.get('Action', 0)
    if Action == 'InvokeReq':
        text = payload.get('Text', 0)
        print("使用者說了:" + text)

    Commands = payload.get('Commands', 0)
    if Commands != 0:
        flag = False

        for ele in payload['Commands']:
            # print(ele)
            myType = ele.get('Type', 0)
            if myType == '01':
                tUrl = ele.get('tUrl', 0)
                if tUrl != 0:
                    print("說話中...:" + tUrl)
                    Media = Instance.media_new(tUrl)
                    player.set_media(Media)
                    player.play()

                    content = ele.get('Content', 0)
                    if content != 0 and not flag:
                        flag = True
                        print("回應的文字:" + content)

            elif myType == '04':
                content = ele.get('Content', 0)
                if content != 0 and not flag:
                    flag = True
                    print("回應的文字:" + content)

            else:
                print(payload)


# Assuming Energy threshold upper than 30 dB
Threshold = 200

SHORT_NORMALIZE = (1.0 / 32768.0)
chunk = 2400
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
swidth = 2
Max_Seconds = 3

TimeoutSignal = int((RATE / chunk * Max_Seconds) + 2)
silence = True
Time = 0
samples = []


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
    # stream.close()
    # p.terminate()

    FileNameTmp = 'REC/rec{0}.wav'.format(getLocalTime())
    wf = wave.open(FileNameTmp, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(WriteData))
    wf.close()


def KeepRecord(TimeoutSignal, LastBlock):
    global isPlaying
    global samples, silence, Time

    samples = []
    samples.append(LastBlock)
    for i in range(0, TimeoutSignal):
        try:
            data = GetStream(chunk)
        except:
            continue
        samples.append(data)

        message = bytearray(b'\x01')
        message.extend(data)
        client.publish(asr, bytes(message))
        time.sleep(0.05)

    print("end record ")
    client.publish(asr, b'\x02')
    isPlaying = True

    # print("write to File")
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


print("waiting for Speech")
print(silence)
while True:
    client.loop(.1)
    '''
    if state == 0:
        if player.get_state() == vlc.State.Opening:
            state = 1

    elif state == 1:
        if player.get_state() == vlc.State.Ended:
            state = 0
            silence = True
            Time = 0
            stream.start_stream()
            print("waiting for Speech")
    '''

    # if not isPlaying and silence:
    if silence:
        try:
            input = GetStream(chunk)

        except:
            continue

        rms_value = int(rms(input))
        print(rms_value)

        if (rms_value > Threshold):
            print('rms:{0}'.format(rms_value))
            silence = False
            LastBlock = input
            print("Recording....")
            client.publish(asr, b'\x00')
            KeepRecord(TimeoutSignal, LastBlock)

        Time = Time + 1
        if (Time > TimeoutSignal):
            Time = 0
            # print("Time Out No Speech Detected")
'''
'''

'''
text = input('請輸入任務')
client.publish(req, serviceInvoke(text))
client.loop_start()
client.loop_forever(retry_first_connection=True)
publish.single(req, payload, hostname=hostname, port=port)
'''
'''
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
'''

'''
import snowboydecoder
import signal

interrupted = False


def signal_handler(signal, frame):
    global interrupted
    interrupted = True


def interrupt_callback():
    global interrupted
    return interrupted


def on_hot_word():
    global detector
    snowboydecoder.play_audio_file()
    detector.terminate()
    print("Restarting...")


model = 'resources/snowboy.umdl'
# capture SIGINT signal, e.g., Ctrl+C
# signal.signal(signal.SIGINT, signal_handler)
detector = snowboydecoder.HotwordDetector(model, sensitivity=0.5)
print('Listening... Press Ctrl+C to exit')

# main loop
detector.start(detected_callback=on_hot_word,
               interrupt_check=interrupt_callback,
               sleep_time=0.03)

detector.terminate()
'''
