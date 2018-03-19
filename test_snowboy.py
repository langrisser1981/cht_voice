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

interrupted = False


def signal_handler(signal, frame):
    global interrupted
    interrupted = True


def interrupt_callback():
    global interrupted
    return interrupted


def on_hot_word(hotword):
    snowboydecoder.play_audio_file()
    detector.terminate()

    voice_service = {
        'snowboy': ["echo", "谷歌助理"],
        'smart_mirror': ["python3", "./mqtt.py"]
    }
    cmd = voice_service.get(hotword, ["echo", "錯誤的關鍵字"])
    pro = subprocess.Popen(cmd).wait()

    print("重新啟動""關鍵字""偵聽程式...")
    os.execv(sys.executable, ['python3'] + sys.argv)


# capture SIGINT signal, e.g., Ctrl+C
# signal.signal(signal.SIGINT, signal_handler)

models = ['resources/snowboy.umdl', 'resources/smart_mirror.umdl']
sensitivity = [0.5] * len(models)
detector = snowboydecoder.HotwordDetector(models, sensitivity=sensitivity)

callbacks = [
    lambda: on_hot_word('snowboy'),
    lambda: on_hot_word('smart_mirror')
]

print('Listening... Press Ctrl+C to exit')

# main loop
try:
    detector.start(detected_callback=callbacks,
                   interrupt_check=interrupt_callback,
                   sleep_time=0.03)
    detector.terminate()

except KeyboardInterrupt:
    print('鍵盤中斷')
