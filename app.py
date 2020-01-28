import csv
import json
import models
import os
import parse
import random
import requests
import sys

from copy import copy
from flask import Flask, request
from flask_heroku import Heroku
from flask_sqlalchemy import SQLAlchemy
from groupme_message_type import ERROR_STRING, HELP_STRING, MessageType
from textblob import TextBlob
from typing import Any, Dict, List, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

app = Flask(__name__)

# Used for local testing.
if app.debug:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

# Initializing the app.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
heroku = Heroku(app)
db = SQLAlchemy(app)
Score = models.create_score_data_object(db)
Rank = models.create_rank_data_object(db)
init_rank = False


@app.route('/', methods=['POST'])
def webhook():
    """
    Receives the JSON object representing the GroupMe message, and
    sends a response, if necessary.

    Returns:
        status [str]: 'ok' or 'not ok'.
        code   [int]: Standard error code.
    """
    message: Dict[str, Any] = request.get_json()
    admin: List[str] = os.getenv('ADMIN').split(':')

    sender: str = message.get('sender_id', None)
    text: str = message.get('text', None)

    # Ignore messages sent from the bot.
    if sender_is_bot(message):
        return 'ok', 200

    # Initializing the rankings should only happen once.
    if init_rank:
        print("Initializing rankings..")
        __init_rankings()

    message_type: MessageType = MessageType.NOTHING
    if text.startswith("/score"):
        if sender in admin:
            message_type = MessageType.ADMIN_SCORE
        else:
            message_type = MessageType.NON_ADMIN_SCORE
    elif (text.startswith("/leaderboard") or
          text.startswith("/lb")):
        message_type = MessageType.LEADERBOARD
    elif (text.startswith("/check")) and sender in admin:
        message_type = MessageType.ADMIN_VERIFY
    elif (text.startswith("/help")):
        message_type = MessageType.HELP
    elif "scorebot" in text.lower():
        message_type = MessageType.TAUNTING

    return process_message(message, message_type)


def process_message(message: Dict, message_type: MessageType)\
        -> Tuple[str, int]:
    response: str = ''
    if message_type == MessageType.ADMIN_SCORE:
        response = score(message)
    elif message_type == MessageType.LEADERBOARD:
        response = generate_leaderboard()
    elif message_type == MessageType.ADMIN_VERIFY:
        messages = get_messages_before_id(message.get('id'))
        response = filter_messages_for_scores(messages)
    elif message_type == MessageType.HELP:
        response = HELP_STRING
    elif message_type == MessageType.TAUNTING:
        response = taunt(message.get('text', ''))

    return send_response(response)


def send_response(response: Any):
    if not app.debug:
        if isinstance(response, list):
            for msg in response:
                reply(msg)
        elif response != '':
            reply(response)
    print(response)
    return 'ok', 200


def taunt(text: str):
    blob = TextBlob(text)
    polarity, subjectivity = blob.sentiment
    sentiment = 'neutral'
    if polarity < -0.3:
        sentiment = 'bad'
    elif polarity > 0.3:
        sentiment = 'good'
    return get_emotional_response(sentiment)


def get_emotional_response(level):
    file = f"resources/responses/{level}.csv"
    response = ''
    with open(file, 'r') as responses:
        reader = list(csv.reader(responses))
        response = random.choice(reader)[0]

    return response


def score(message):
    text: str = message.get('text', '')
    (ok, parsed) = parse.score_parse(text)
    msg: str = ''
    if not ok:
        msg += ERROR_STRING
    else:
        db_data, note = _process_data_for_db(parsed, message)
        players = db_data[:4]
        if len(players) == 0:
            msg += note
        else:
            add_to_db(*db_data)
            msg += f"Match recorded:\n {players[0]} and {players[1]}"
            msg += f" v. {players[2]} and {players[3]}.\n"
            if len(note) > 0:
                msg += "-------------------------\n"
                msg += note

    return msg


def generate_leaderboard():
    ranks = Rank.query.all()
    ranks = sorted(Rank.query.all(), key=lambda x: x.rank)[:10]
    msg = 'LEADERBOARD\n'.rjust(10)
    msg += '-------------------------\n'

    for player in ranks:
        name = player.name
        rank = player.rank
        msg += f"{rank}   -   {name}\n"

    return msg


def _process_data_for_db(parsed, message):
    ids_var = os.getenv('IDS').split(':')
    convert_dict = dict()
    for id_name in ids_var:
        id, name = id_name.split('%')
        convert_dict[id] = name

    # Convert nicknames to actual names.
    parsed_mentions = parsed[:4]
    me = message.get('sender_id', None)
    mentions = message.get('attachments', [{}])[0].get('user_ids', [])
    timestamp = message.get('created_at', None)

    people = list(map(lambda x: x[0], parsed_mentions))
    j: int = 0
    for i, person in enumerate(people):
        if person.lower() == "me":
            parsed[i][0] = convert_dict[me]
        else:
            parsed[i][0] = convert_dict[mentions[j]]
            j += 1

    # Get it primed for the database.
    parsed = list(parsed)
    players = [list(parsed[i]) for i in range(4)]
    score_12, score_34 = list(parsed[-1])

    player_1, player_2, player_3, player_4 = list(map(lambda x: x[0],
                                                      players))
    points = list(map(lambda x: 0 if len(x) == 1 else x[1], players))
    sinks = list(map(lambda x: 0 if len(x) == 1 else x[2], players))
    note: str = ''
    db_data: List = []

    # Error checking.
    if max(score_12, score_34) < 7:
        note = "Games to less than 7 are for the weak. Disregarded."

    if abs(score_12 - score_34) < 2:
        note = "It's win by 2, numbnut."

    if (sum(points[:2]) != 0):
        if (sum(points[:2]) != score_12):
            note = ("Your individual points don't add up to your total."
                    " *cough* First team. *cough*")

    if (sum(points[2:]) != 0):
        if (sum(points[2:]) != score_34):
            note = ("Your individual points don't add up to your total."
                    " *cough* Second team. *cough*")

    if sum(sinks) > (score_12 + score_34):
        note = "More sinks than total points? Nice."

    for player in range(4):
        if points[player] < sinks[player]:
            note = (f"I don't know how {players[player][0]} sunk more "
                    "times than scored, but I'm impressed.")

    if len(note) == 0:
        db_data = (player_1, player_2, player_3, player_4, score_12,
                   score_34, points, sinks, timestamp)
    if abs(score_12 - score_34) > 4:
        note = "I smell a naked lap coming."

    return db_data, note


def add_to_db(player, partner, opponent_1, opponent_2,
              score, opp_score, mugs, sinks, timestamp):
    indata = Score(player, partner, opponent_1, opponent_2,
                   score, opp_score, mugs, sinks, timestamp)
    data = copy(indata.__dict__)
    del data["_sa_instance_state"]
    try:
        if app.debug:
            return True
        db.session.add(indata)
        db.session.commit()
    except Exception as e:
        print(f"FAILED entry: {json.dumps(data)}\n")
        print(e)
        sys.stdout.flush()
        return False
    return True


def __init_rankings():
    """ Uses a csv file of GroupMe IDs to real names to initialize
    the database. """
    raw_ids_names = os.environ.get('IDS', '').split(':')
    for item in raw_ids_names:
        groupme_id, name = item.split('%')
        # Initial rankings are all 1 for now.
        indata = Rank(groupme_id, name, 1)
        data = copy(indata.__dict__)
        del data["_sa_instance_state"]
        if app.debug:
            continue
        try:
            db.session.add(indata)
            db.session.commit()
        except Exception as e:
            print(f"FAILED entry: {json.dumps(data)}\n")
            print(e)
            sys.stdout.flush()
            return False


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


def get_messages_before_id(before_id):
    group_id = os.environ.get('GROUPME_GROUP_ID')
    token = os.environ.get('ACCESS_TOKEN')
    url = f'https://api.groupme.com/v3/groups/{group_id}/messages'
    params = {'before_id': str(before_id),
              'token': token,
              'limit': 10}

    msg_rqst = requests.get(url, params=params)
    return msg_rqst.json()['response']


def filter_messages_for_scores(messages):
    admin: List[str] = os.getenv('ADMIN').split(':')
    msgs = []
    last_updated_game = Score.query.order_by(Score.timestamp.desc()).first()
    last_timestamp = last_updated_game.timestamp

    for message in messages.get('messages'):
        text = message.get('text')
        if text.startswith("/score"):
            timestamp = message.get("created_at")
            favorites = message.get('favorited_by')

            for favorite in favorites:
                if (favorite in admin) and (timestamp > last_timestamp):
                    msgs.append(score(message))

    return msgs


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
