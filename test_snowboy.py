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
    snowboydecoder.play_audio_file()
    print("snowboy...")


model = 'resources/snowboy.umdl'
# capture SIGINT signal, e.g., Ctrl+C
# signal.signal(signal.SIGINT, signal_handler)
detector = snowboydecoder.HotwordDetector(model, sensitivity=0.5)
print('Listening... Press Ctrl+C to exit')

# main loop
try:
    detector.start(detected_callback=on_hot_word,
               interrupt_check=interrupt_callback,
               sleep_time=0.03)
    detector.terminate()

except KeyboardInterrupt:
    print('bye~')

