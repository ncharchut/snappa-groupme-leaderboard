import os
# import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from flask import Flask, request
import requests

app = Flask(__name__)
bot_id = "a6c28ab43d7e95d98a7ce1fd6f "


@app.route('/', methods=['POST'])
def webhook():
    # 'message' is an object that represents a single GroupMe message.
    message = request.get_json()
    print(f"name: {message['name']}")
    print(f"msg : {message['text']}")
    print(f"name: {request.args['name']}")
    print(f"msg : {request.args['text']}")

    # TODO: Your bot's logic here

    return "ok", 200


# Send a message in the groupchat
def reply(msg):
    url = 'https://api.groupme.com/v3/bots/post'
    data = {'bot_id': bot_id,
            'text': msg}
    request = Request(url, urlencode(data).encode())
    json = urlopen(request).read().decode()
    print(json)


# Send a message with an image attached in the groupchat
def reply_with_image(msg, imgURL):
    url = 'https://api.groupme.com/v3/bots/post'
    urlOnGroupMeService = upload_image_to_groupme(imgURL)
    data = {'bot_id':      bot_id,
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
