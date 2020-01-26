import os
# import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from flask import Flask, request
import requests
from typing import Any, List, Dict

app = Flask(__name__)


@app.route('/', methods=['POST'])
def webhook():
    # 'message' is an object that represents a single GroupMe message.
    message: Dict[str, Any] = request.get_json()
    admin: List[str] = os.environ.get('ADMIN').split(':')

    sender: str = message.get('sender_id', None)
    text: str = message.get('text', None)

    if not text.startswith("/score"):
        print("don't care!")
        return "ok", 200

    msg: str
    if sender not in admin:
        msg = "Lesser beings aren't granted such powers."
    else:
        msg = "Match recorded."

    reply(msg)
    return "ok", 200


# Send a message in the groupchat
def reply(msg):
    url = 'https://api.groupme.com/v3/bots/post'
    data = {'bot_id': os.environ.get('BOT_ID', None),
            'text': msg}
    if data['bot_id'] is None:
        print("Set BOT_ID environment variable")
        return

    # print(data)
    request = Request(url, urlencode(data).encode())
    # response = requests.post(url, data)
    # print(response.text)
    json = urlopen(request).read().decode()
    print(json)


# Send a message with an image attached in the groupchat
def reply_with_image(msg, imgURL):
    url = 'https://api.groupme.com/v3/bots/post'
    urlOnGroupMeService = upload_image_to_groupme(imgURL)
    data = {'bot_id':      os.environ.get('BOT_ID', None),
            'text':        msg,
            'picture_url': urlOnGroupMeService}
    request = Request(url, urlencode(data).encode())
    json = urlopen(request).read().decode()
    print(json)


# Uploads image to GroupMe's services and returns the new URL
def upload_image_to_groupme(imgURL):
    imgRequest = requests.get(imgURL, stream=True)
    filename = 'temp.png'
    # postImage = None
    if imgRequest.status_code == 200:
        # Save Image
        with open(filename, 'wb') as image:
            for chunk in imgRequest:
                image.write(chunk)
    # Send Image
    # headers = {'content-type': 'application/json'}
    url = 'https://image.groupme.com/pictures'
    files = {'file': open(filename, 'rb')}
    payload = {'access_token': 'eo7JS8SGD49rKodcvUHPyFRnSWH1IVeZyOqUMrxU'}
    r = requests.post(url, files=files, params=payload)
    imageurl = r.json()['payload']['url']
    os.remove(filename)
    return imageurl


# Checks whether the message sender is a bot
def sender_is_bot(message):
    return message['sender_type'] == "bot"


if __name__ == "__main__":
    app.run(host='0.0.0.0')
