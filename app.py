import json
import os
import parse
import requests
import sys

from copy import copy

from flask import Flask, request
from flask_heroku import Heroku
from flask_sqlalchemy import SQLAlchemy
from typing import Any, List, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# from flask import Flask, render_template, url_for
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
heroku = Heroku(app)
db = SQLAlchemy(app)


class Score(db.Model):
    """ Schema for score submission for a given match. """
    __tablename__ = 'snappa-scores'

    id = db.Column(db.Integer, primary_key=True)
    # Player id's
    player_1 = db.Column(db.String())
    player_2 = db.Column(db.String())
    player_3 = db.Column(db.String())
    player_4 = db.Column(db.String())

    # Team Scores
    score_12 = db.Column(db.Integer)
    score_34 = db.Column(db.Integer)

    # Mug taps per player
    mugs_1 = db.Column(db.Integer)
    mugs_2 = db.Column(db.Integer)
    mugs_3 = db.Column(db.Integer)
    mugs_4 = db.Column(db.Integer)

    # Sinks per player
    sinks_1 = db.Column(db.Integer)
    sinks_2 = db.Column(db.Integer)
    sinks_3 = db.Column(db.Integer)
    sinks_4 = db.Column(db.Integer)

    def __init__(self, team_1, team_2, score_1, score_2, mugs=(0, 0, 0, 0),
                 sinks=(0, 0, 0, 0)):
        self.player_1, self.player_2 = team_1
        self.player_3, self.player_4 = team_2
        self.score_12 = score_1
        self.score_34 = score_2
        self.mugs_1, self.mugs_2, self.mugs_3, self.mugs_4 = mugs
        self.sinks_1, self.sinks_2, self.sinks_3, self.sinks_4 = sinks

    def __repr__(self):
        return f"<id {self.id}>"

    def __team_of_two(self, team):
        """ Will be used when database supports 1 v. 1 matches. """
        return isinstance(team, list) or isinstance(team, tuple)


@app.route('/', methods=['POST'])
def webhook():
    # 'message' is an object that represents a single GroupMe message.
    message: Dict[str, Any] = request.get_json()
    admin: List[str] = os.getenv('ADMIN').split(':')

    sender: str = message.get('sender_id', None)
    text: str = message.get('text', None)

    if not text.startswith("/score"):
        print(message)
        print("Don't care.")
        return "ok", 200

    msg: str
    parsed: List[Any] = []
    if sender not in admin:
        msg = "Lesser beings aren't granted such powers."
        print(msg)
    else:
        ok, parsed = parse.score_parse(text)
        if not ok:
            msg = """Invalid.
            Must be `/score @A @B [@C @D] score1-score2`.
            /score @A [[m1 s1]] @B [[m2 s2]]\
               @C [[m3 s3]] @D [[m4 s4]] SCORE_AB [-,|] SCORE_CD"""
        else:
            msg = "Match recorded."
            db = _process_data_for_db(parsed, message)
            players = list(map(lambda x: x[0], db[:4]))
            msg += f" Players identified are: {players}"

    if not app.debug:
        reply(msg)
    else:
        print(msg)
        print(parsed)
    print(message)
    return "ok", 200


def _process_data_for_db(parsed, message):
    ids_var = os.getenv('IDS').split(':')
    convert_dict = dict()
    for id_name in ids_var:
        id, name = id_name.split('-')
        convert_dict[id] = name

    parsed_mentions = parsed[:4]
    me = message.get('sender_id', None)
    mentions = message.get('attachments', [{}])[0].get('user_ids', [])

    people = list(map(lambda x: x[0], parsed_mentions))
    j: int = 0
    for i, person in enumerate(people):
        if person.lower() == "me":
            parsed[i][0] = convert_dict[me]
        else:
            parsed[i][0] = convert_dict[mentions[j]]
            j += 1

    return parsed


def add_to_db(team_1, team_2, score_1, score_2, mugs_1, mugs_2):
    indata = Score(team_1, team_2, score_1, score_2, mugs_1, mugs_2)
    data = copy(indata.__dict__)
    del data["_sa_instance_state"]
    try:
        db.session.add(indata)
        db.session.commit()
    except Exception as e:
        print(f"FAILED entry: {json.dumps(data)}\n")
        print(e)
        sys.stdout.flush()
        return False
    return True


# def validate_scoring(message: Dict[str, Any]):
#     mentions: List[str] = message.get('attachments')[0]['user_ids']
#     words: List[str] = message.get('text').split(' ')

#     players = list(map(lambda y: y.lower(),
#                        filter(lambda x: x.startswith('@'), words)))
#     if app.debug:
#         print(f"players: {players}")
#         print(f"mentions: {mentions}")

#     # Accounts for 1v1 or 2v2
#     if '@me' in players:
#         if (len(mentions) + 1) != len(players) or len(players) not in [2, 4]:
#             return False
#     else:
#         if (len(players) != len(mentions)) or len(players) not in [2, 4]:
#             return False

#     return True


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
    response = urlopen(request).read().decode()
    print(response)


# Send a message with an image attached in the groupchat
def reply_with_image(msg, imgURL):
    url = 'https://api.groupme.com/v3/bots/post'
    urlOnGroupMeService = upload_image_to_groupme(imgURL)
    data = {'bot_id':      os.environ.get('BOT_ID', None),
            'text':        msg,
            'picture_url': urlOnGroupMeService}
    request = Request(url, urlencode(data).encode())
    response = urlopen(request).read().decode()
    print(response)


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
    app.debug = False
    app.run(host='0.0.0.0')
