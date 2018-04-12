import paho.mqtt.publish as publish
from urllib.parse import urlparse


def send(cmd):
    url_str = 'mqtt://35.185.154.72:1883'
    url = urlparse(url_str)
    host = url.hostname
    port = url.port

    topic = 'kkbox/info'
    payload = cmd

    # If broker asks user/password.
    auth = {'username': "", 'password': ""}
    # If broker asks client ID.
    client_id = ""
    publish.single(topic, payload, hostname=host, port=port)
    # publish.single(topic, payload, qos=1, host=host, auth=auth, client_id=client_id)


import sys, os, time, signal
import paho.mqtt.client as mqtt

client = None
mqtt_looping = False

TOPIC_ROOT = "kkbox/info"


def on_connect(mq, userdata, rc, _):
    # subscribe when connected.
    mq.subscribe(TOPIC_ROOT)
    send('https://event.kkbox.com/content/song/4kxvr3wPWkaL9_y3o_')


def on_message(mq, userdata, msg):
    print('topic: {}'.format(msg.topic))
    print('payload: {}'.format(msg.payload))
    print('qos: {}'.format(msg.qos))
    stop_all()


def mqtt_client_thread():
    global client, mqtt_looping
    client_id = ""  # If broker asks client ID.
    client = mqtt.Client(client_id=client_id)

    # If broker asks user/password.
    user = ""
    password = ""
    client.username_pw_set(user, password)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect("35.185.154.72")
    except:
        print('MQTT Broker is not online. Connect later.')

    mqtt_looping = True
    print('Looping...')

    # mqtt_loop.loop_forever()
    cnt = 0
    while mqtt_looping:
        client.loop()

        cnt += 1
        if cnt > 20:
            try:
                client.reconnect()  # to avoid 'Broken pipe' error.
            except:
                time.sleep(1)
            cnt = 0

    print('quit mqtt thread')
    client.disconnect()


def stop_all(*args):
    global mqtt_looping
    mqtt_looping = False


if __name__ == '__main__':
    mqtt_client_thread()

    print('exit program')
    sys.exit(0)
