LANG_CODE = 'en-US'  # Language to use

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
import paho.mqtt.publish as publish
from urllib.parse import urlparse
import json
import datetime
import calendar
import time

import pyaudio
import wave
import audioop
from collections import deque
import os
import math
import struct
import sys
import threading
import kkbox
from event import *
import sys, logging


def sendToPhone(cmd):
    url_str = 'mqtt://35.185.154.72:1883'
    url = urlparse(url_str)
    host = url.hostname
    port = url.port
    ##If broker asks user/password.
    auth = {'username': "", 'password': ""}
    ##If broker asks client ID.
    client_id = ""
    
    topic = 'kkbox/info'
    payload = cmd
    publish.single(topic, payload, hostname=host, port=port)
    # publish.single(topic, payload, qos=1, host=host, auth=auth, client_id=client_id)


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
    localTime = getLocalTime()
    index = increase()
    ##reqId = 'EID{0}'.format(time.mktime(localTime.timetuple()) + 1e-6 * localTime.microsecond)
    reqId = 'EID{0}{1:0>2d}{2:0>2d}{3:0>2d}{4:0>2d}{5:0>5d}'.format(localTime.year, localTime.month, localTime.day, localTime.hour, localTime.minute, index)
    return reqId


class CHT(object):
    ##中華遠端連線相關的定義
    hostname = 'ibobby.ai.hinet.net'
    port = 8883
    venderId = 'compal'
    ##用谷歌的語音轉文字
    deviceId = 'compal0x002'
    Token = '59706b8d4f1d657a96878060ac3ca647'
    ##用中華的語音轉文字
    deviceId = 'compal0x001'
    Token = 'd0c451e67005ff99b860d54ef99e5428'

    req = 'ai/speaker/{0}/{1}/req'.format(venderId, deviceId)
    rsp = 'ai/speaker/{0}/{1}/rsp'.format(venderId, deviceId)
    asr = 'ai/speaker/{0}/{1}/asr'.format(venderId, deviceId)
    asr_debug = 'ai/speaker/{0}/{1}/asr_debug'.format(venderId, deviceId)

    ##聲音相關的定義
    # Microphone stream config.
    CHUNK = 2400  # CHUNKS of bytes to read each time from mic
    # CHUNK = 1024  # CHUNKS of bytes to read each time from mic
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    THRESHOLD = 1800  # The threshold intensity that defines silence
    # and noise signal (an int. lower than THRESHOLD is silence).
    SILENCE_LIMIT = 1  # Silence limit in seconds. The max ammount of seconds where
    # only silence is recorded. When this time passes the
    # recording finishes and the file is delivered.
    PREV_AUDIO = 0.5  # Previous audio (in seconds) to prepend. When noise
    # is detected, how much of previously recorded audio is
    # prepended. This helps to prevent chopping the beggining
    # of the phrase.
    EVENT_MQTT_Connected = Event(name='mqtt_connected')
    EVENT_Conversation_Over = Event(name='conversation_over')
    
    
    def __register(self):
        json_payload = {
            'Action': 'RegisterReq',
            'Time': getUTC(),
            'RequestID': getReqId(),
            'Version': '1.1'
        }
        payload = json.dumps(json_payload, sort_keys=True, ensure_ascii=False)
        return payload
    
    
    def __serviceInvoke(self, text):
        json_payload = {
            'Action': 'InvokeReq',
            'Time': getUTC(),
            'RequestID': getReqId(),
            'Text': text
        }
        payload = json.dumps(json_payload, sort_keys=True, ensure_ascii=False)
        print('我的問題是:' + json_payload.get('Text') + ', 時間:' + json_payload.get('Time') + ', 請求:' + json_payload.get('RequestID'))
        return payload
    
    
    def __on_connect(self, client, userdata, flag, rc):
        print("中華電信連線" + ('成功' if rc == 0 else '失敗'))
        self.__client.subscribe(CHT.rsp)
        self.__client.subscribe(CHT.asr_debug)
        subprocess.run(['aplay', 'wellcome.wav'])
        self.__eventManager.dispatchEvent(self.EVENT_MQTT_Connected)
        
        
    def __testServer(self):
        text = '請問張惠妹是誰'
        text = '今天有那些行程'
        text = '今天仁寶的股價是多少'
        text = '今天新北市天氣如何'
        text = '我要聽張惠妹的姊妹'
        self.__client.publish(CHT.req, self.__serviceInvoke(text))
        
        
    def __on_disconnect(self, client, userdata, rc):
        print("中華電信斷線")
        
        
    ##處理遠端回傳的訊息
    def __on_message(self, client, userdata, msg):
        ##print(msg.topic + ", " + str(msg.payload))
        payload = json.loads(msg.payload.decode('utf-8'))
        end = False
        flag = False
        
        if msg.topic == CHT.asr_debug:
            if 'Text' in payload:
                print("遠端收到使用者說了:" + payload.get('Text'))
                
        elif msg.topic == CHT.rsp:
            end = True
            if 'Commands' in payload:
                for ele in payload['Commands']:
                    ##print(ele)
                    myType = ele.get('Type', 0)
                    if myType == '01':
                        content = ele.get('Content', 0)
                        if content != 0 and not flag:
                            flag = True
                            print("回應的文字:" + content)
                            
                        tUrl = ele.get('tUrl', 0)
                        print("說話中:" + tUrl)
                        subprocess.run(['ffplay', '-nodisp', '-autoexit', tUrl])
                        ##result = subprocess.run(['ffplay', '-autoexit', tUrl], stdout=subprocess.PIPE)
                        ##print(result.stdout)
                        
                    elif myType == '02':
                        content = ele.get('Content', 0)
                        if content != 0:
                            print("歌曲資訊:" + content)
                            
                        ##url = 'https://widget.kkbox.com/v1/?id=4kxvr3wPWkaL9_y3o_&type=song&terr=TW&lang=TC&autoplay=true&loop=true'
                        ##result = subprocess.Popen(['chromium-browser', url], stdout=subprocess.PIPE)
                        ##print(result.stdout)
                            
                        track_id = content
                        track_info = kkboxapi.track_fetcher.fetch_track(track_id)
                        url = track_info['url']
                        print('歌曲資訊連結是:{}'.format(url))
                        sendToPhone(url)
                        
                        tickets = kkboxapi.ticket_fetcher.fetch_media_provision(track_id)
                        url = tickets['url']
                        print('下載位置連結是:{}'.format(url))
                        
                        print('底下是播放資訊')
                        subprocess.run(['ffplay', '-nodisp', '-autoexit', url])
                        
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
            ##self.__active = False
            ##self.__job.stop()
            ##sys.exit()
            print('辨識結束')
            self.__eventManager.dispatchEvent(self.EVENT_Conversation_Over)
            
            
    ##以上是中華電信語音辨識，回傳訊息處理的程式
    ##以下是音訊處理的程式
            
            
    def audio_int(self, num_samples=50):
        """
            Gets average audio intensity of your mic sound. You can use it to get
            average intensities while you're talking and/or silent. The average
            is the avg of the 20% largest intensities recorded.
        """
        pa = pyaudio.PyAudio()
        stream = pa.open(format=CHT.FORMAT,
                                channels=CHT.CHANNELS,
                                rate=CHT.RATE,
                                input=True,
                                frames_per_buffer=CHT.CHUNK)
        
        print('Getting intensity values from mic.')
        values = [math.sqrt(abs(audioop.avg(stream.read(CHT.CHUNK), 4)))
              for x in range(num_samples)]
        values = sorted(values, reverse=True)
        avg = sum(values[:int(num_samples * 0.2)]) / int(num_samples * 0.2)
        print('Average audio intensity is {0}'.format(avg))
        stream.close()
        pa.terminate()
        return avg
    
    
    def __listen_for_speech(self, threshold=THRESHOLD, num_phrases=-1):
        """
            Listens to Microphone, extracts phrases from it and sends it to
            Google's TTS service and returns response. a "phrase" is sound
            surrounded by silence (according to threshold). num_phrases controls
            how many phrases to process before finishing the listening process
            (-1 for infinite).
        """
        ##Open stream
        pa = pyaudio.PyAudio()
        stream = pa.open(format=CHT.FORMAT,
                                channels=CHT.CHANNELS,
                                rate=CHT.RATE,
                                input=True,
                                frames_per_buffer=CHT.CHUNK)
        
        print('Listening mic. ')
        audio2send = []
        cur_data = ''  # current chunk  of audio data
        rel = CHT.RATE / CHT.CHUNK
        slid_win = deque(maxlen=int(CHT.SILENCE_LIMIT * rel) + 1)
        ##Prepend audio from 0.5 seconds before noise was detected
        prev_audio = deque(maxlen=int(CHT.PREV_AUDIO * rel) + 1)
        
        started = False
        n = num_phrases
        
        while (num_phrases == -1 or n > 0):
            cur_data = stream.read(CHT.CHUNK)
            slid_win.append(math.sqrt(abs(audioop.avg(cur_data, 4))))
            ##print slid_win[-1]
            if (sum([x > CHT.THRESHOLD for x in slid_win]) > 0):
                if (not started):
                    print('Starting record of phrase')
                    self.__client.publish(CHT.asr, b'\x00')
                    started = True
                    
                payload = bytearray(b'\x01')
                payload.extend(cur_data)
                self.__client.publish(CHT.asr, bytes(payload))
                ##time.sleep(0.05)
                audio2send.append(cur_data)
                
            elif (started is True):
                print('Finished')
                self.__client.publish(CHT.asr, b'\x02')
                
                ##The limit was reached, finish capture and deliver.
                filename = self.__save_speech(list(prev_audio) + audio2send, pa)
                ##Remove temp file. Comment line to review.
                ##os.remove(filename)
                
                ##Reset all
                started = False
                slid_win = deque(maxlen=int(CHT.SILENCE_LIMIT * rel) + 1)
                prev_audio = deque(maxlen=int(CHT.PREV_AUDIO * rel) + 1)
                audio2send = []
                n -= 1
                
            else:
                prev_audio.append(cur_data)
                
        print('Done recording')
        stream.close()
        pa.terminate()
    
    
    def __save_speech(self, data, pa):
        """
            Saves mic data to temporary WAV file. Returns filename of saved file
        """
        filename = 'REC/output_' + str(int(time.time())) + '.wav'
        
        ##writes data to WAV file
        ##這邊記得要先在資料開頭加b，將資料宣告為位元組，否則會出錯
        data = b''.join(data)
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHT.CHANNELS)
        wf.setsampwidth(pa.get_sample_size(CHT.FORMAT))
        wf.setframerate(CHT.RATE)
        wf.writeframes(data)
        wf.close()
        return filename
    
    
    def __eventProcess(self, event):
        print(event.name)
        if event.name == 'conversation_over':
            self.func()
            
        pass
    
    
    def __loop(self):
        try:
            while self.__active:
                self.__client.loop(.1)
                
        except KeyboardInterrupt:
            print('鍵盤中斷')
            
            
    def listen(self):
        ##self.__testServer()
        ##self.audio_int()
        self.__listen_for_speech(1000, 1)  # listen to mic.
        
        
    def addEventListener(self, type, func):
        self.func = func
        
        
    def __init__(self):
        self.__client = mqtt.Client()
        self.__client.username_pw_set(CHT.Token, CHT.Token)
        self.__client.tls_set('ROOTeCA_64.crt')
        ##self.__client.tls_set_context(context=ssl.create_default_context())
        self.__client.on_connect = self.__on_connect
        self.__client.on_disconnect = self.__on_disconnect
        self.__client.on_message = self.__on_message
        
        self.__eventManager = EventManager()
        self.__eventManager.start()
        self.__eventManager.addEventListaner(self.EVENT_MQTT_Connected.name, self.__eventProcess)
        self.__eventManager.addEventListaner(self.EVENT_Conversation_Over.name, self.__eventProcess)
        
        self.__active = True
        self.__job = threading.Thread(target=self.__loop)
        self.__job.start()
        
        self.__client.connect(CHT.hostname, CHT.port)
        ##self.__client.publish(CHT.req, self.__register())
    
    
    def exit(self):
        self.__eventManager.removeEventListaner(EVENT_MQTT_Connected.name, self.__mqtt_connected)
        self.__eventManager.removeEventListaner(EVENT_Conversation_Over.name, self.__callback)
        self.__eventManager.stop()
