import subprocess

# result = subprocess.run(['ffplay', '-autoexit', 'http://ibobby.ai.hinet.net:8888/tts/ch/synthesisRaw?inputText=%E8%AB%8B%E5%95%8F%E6%82%A8%E8%A6%81%E5%95%8F%E7%9A%84%E4%BD%8D%E7%BD%AE%EF%BC%9F'], stdout=subprocess.PIPE)
# print(result.stdout)

url = 'https://widget.kkbox.com/v1/?id=4kxvr3wPWkaL9_y3o_&type=song&terr=TW&lang=TC&autoplay=true&loop=true'
result = subprocess.Popen(['chromium-browser', url], stdout=subprocess.PIPE)
print(result.stdout)
