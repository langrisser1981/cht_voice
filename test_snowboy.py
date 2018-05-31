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

import snowboydecoder
import signal
import os, sys
import subprocess
import event
from cht import *

class Butler():
    ##models = ['resources/snowboy.umdl', 'resources/smart_mirror.umdl']
    models = ['resources/smart_mirror.umdl', 'resources/snowboy.umdl']
    sensitivity = [0.9] * len(models)
    interrupted = False
    
    
    def __interrupt_callback(self):
        return self.interrupted
    
    
    def __on_hot_word(self, hotword):
        snowboydecoder.play_audio_file()
        self.__detector.terminate()
        
        if hotword == 'cht':
            self.__cht.listen()
            pass
        
        else:
            voice_service = {
                            'google': ["python3", "./google/pushtotalk.py", '--project-id', 'massive-tuner-194305', '--device-model-id',
                            'massive-tuner-194305-assistant-sdk-light-qev3ip'],
                            'cht': ["python3", "./cht.py"]
            }
            cmd = voice_service.get(hotword, ["echo", "錯誤的關鍵字"])
            pro = subprocess.Popen(cmd).wait()
            print("重新開始'啟動關鍵字'偵聽程式...")
            os.execv(sys.executable, ['python3'] + sys.argv)
            
            
    def __init__(self):
        self.__cht = CHT()
        self.__cht.addEventListener('conversation_over', self.__loop)
        self.__loop()
        
        
    def __loop(self):
        callbacks = [
            lambda: self.__on_hot_word('google'),
            lambda: self.__on_hot_word('cht')
        ]
        
        print('Listening... Press Ctrl+C to exit')
        try:
            self.__detector = snowboydecoder.HotwordDetector(self.models, sensitivity=self.sensitivity)
            self.__detector.start(detected_callback=callbacks,
                interrupt_check=self.__interrupt_callback,
                sleep_time=0.03)
            
        except KeyboardInterrupt:
            self.__cht.exit()
            self.__detector.terminate()
            print('鍵盤中斷')
            

butler = Butler()
