import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from flask import Flask, request
import requests
from typing import Any, List, Dict

app = Flask(__name__)
DEBUG = False


@app.route('/', methods=['POST'])
def webhook():
    # 'message' is an object that represents a single GroupMe message.
    message: Dict[str, Any] = request.get_json()
    admin: List[str] = os.getenv('ADMIN').split(':')

    sender: str = message.get('sender_id', None)
    text: str = message.get('text', None)

    if not text.startswith("/score"):
        print("Don't care.")
        return "ok", 200

    msg: str
    scores: List[int]
    if sender not in admin:
        msg = "Lesser beings aren't granted such powers."
        print(msg)
    else:
        scores, valid = validate_scoring(message)
        if not valid:
            msg = "Invalid. Must be `/score @A @B [@C @D] score1-score2`."
        else:
            msg = "Match recorded."

    if not DEBUG:
        reply(msg)
    else:
        print(msg)
        print(scores)
    print(message)
    return "ok", 200


def validate_scoring(message: Dict[str, Any]):
    mentions: List[str] = message.get('attachments')[0]['user_ids']
    words: List[str] = message.get('text').split(' ')

    players = list(filter(lambda x: x.startswith('@'), words))

    # Accounts for 1v1 or 2v2
    if (len(players) / 2) not in [1, 2] or\
            (len(mentions) / 2) not in [1, 2]:
        return None, False

    score: List[str] = message.get('text').split('-')
    score_a, score_b = score[0][-2:], score[1][:2]

    try:
        score_a = int(score_a)
        score_b = int(score_b)
    except ValueError:
        return None, False

    return (score_a, score_b), True


# Send a message in the groupchat
def reply(msg):
    url = 'https://api.groupme.com/v3/bots/post'
    data = {'bot_id': os.getenv('BOT_ID'),
            'text': msg}
    if data['bot_id'] is None:
        print("BOT_ID environment variable not set. Please configure with\
              `heroku config:set BOT_ID=ID`.")
        return

    request = Request(url, urlencode(data).encode())
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
