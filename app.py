import csv
import json
import os
import parse
import random
import requests
import sys

from copy import copy

from flask import Flask, request
from flask_heroku import Heroku
from flask_sqlalchemy import SQLAlchemy
from textblob import TextBlob
from typing import Any, List, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

app = Flask(__name__)

if app.debug:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
heroku = Heroku(app)
db = SQLAlchemy(app)
init_rank = False


@app.route('/', methods=['POST'])
def webhook():
    message: Dict[str, Any] = request.get_json()
    admin: List[str] = os.getenv('ADMIN').split(':')

    sender: str = message.get('sender_id', None)
    text: str = message.get('text', None)

    # if sender_is_bot(message):
    #     return 'ok', 200

    msg: str = ''
    if text.startswith("/score"):
        if sender in admin:
            msg = score(message)
    elif (text.startswith("/leaderboard") or
          text.startswith("/lb")):
        msg = generate_leaderboard()
    elif (text.startswith("/check")):
        if sender in admin:
            messages = get_messages_before_id(message.get('id'))
            msgs = filter_messages_for_scores(messages)
            if not app.debug:
                for msg in msgs:
                    reply(msg)
                    print(msg)
                    return "ok", 200
    elif (text.startswith("/help")):
        msg = ("Yo, yo! It's ScoreBot. Here's the lowdown.\n\n"
               "To send a score, you have to be an admin. "
               "Check this chat's topic to see who they are.\n\n"
               "To score a match: \n"
               "\t `/score @A @B [@C @D] score1-score2` or\n"
               "`/score @A [p1 s1] @B [p2 s2]`"
               " @C [p3 s3] @D [p4 s4], SCORE_AB - SCORE_CD`\n\n"
               "Note a couple things here. One, if you log player points"
               " (optional), you must do it for both people on the team."
               "  You must also include the brackets.\n\n"
               "To see the leaderboard (currently meaningless):\n"
               "\t `/leaderboard` or `/lb`\n\n"
               "Games must be to 7, drinking thirds, no questions. "
               "That's all from me, let's toss some dye.")
    elif "scorebot" in text.lower():
        blob = TextBlob(text)
        polarity, subjectivity = blob.sentiment
        if polarity < -0.3:
            msg = get_emotional_response('bad')
        elif polarity < 0.3:
            msg = get_emotional_response('neutral')
        else:
            msg = get_emotional_response('good')
    else:
        print("Don't care.")
        return "ok", 200

    # Initialize the rankings DB. Should only happen once.
    if init_rank:
        print("Initializing rankings..")
        __init_rankings()

    if not app.debug:
        reply(msg)

    print(msg)
    return "ok", 200


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
        msg += """Invalid.
        Must be `/score @A @B [@C @D] score1-score2` or\n
        `/score @A [p1 s1] @B [p2 s2]\
           @C [p3 s3] @D [p4 s4] SCORE_AB , SCORE_CD`"""
    else:
        players, note = _process_data_for_db(parsed, message)
        if len(players) == 0:
            msg += note
        else:
            msg += f"Match recorded: {players[0]} and {players[1]}"
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
    game_id = message.get('id', None)

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

    # Error checking.
    if max(score_12, score_34) < 7:
        return [], "Games to less than 7 are for the weak. Disregarded."

    if abs(score_12 - score_34) < 2:
        return [], "It's win by 2, numbnut."

    if (sum(points[:2]) != 0):
        if (sum(points[:2]) != score_12):
            return [], ("Your individual points don't add up to your total."
                        " *cough* First team. *cough*")

    if (sum(points[2:]) != 0):
        if (sum(points[2:]) != score_34):
            print(sum(points[2:]))
            print(score_34)
            return [], ("Your individual points don't add up to your total."
                        " *cough* Second team. *cough*")

    if sum(sinks) > (score_12 + score_34):
        return [], "More sinks than total points? Nice."

    for player in range(4):
        if points[player] < sinks[player]:
            return [], (f"I don't know how {players[player][0]} sunk more "
                        "times than scored, but I'm impressed.")

    ok = add_to_db(player_1, player_2, player_3, player_4,
                   score_12, score_34, points, sinks, timestamp, game_id)

    if ok:
        print("YAAAAY")
    else:
        print("NOOOO :(")

    # Nakie time.
    if abs(score_12 - score_34) > 4:
        return ([player_1, player_2, player_3, player_4],
                "I smell a naked lap coming.")
    return [player_1, player_2, player_3, player_4], ''


def add_to_db(player, partner, opponent_1, opponent_2,
              score, opp_score, mugs, sinks, timestamp, game_id):
    indata = Score(player, partner, opponent_1, opponent_2,
                   score, opp_score, mugs, sinks, timestamp, game_id)
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


# I tried moving these to a different file but got a circular import
# no matter what :(
class Score(db.Model):
    """ Schema for score submission for a given match. """
    __tablename__ = 'snappa-scores'

    id = db.Column(db.Integer, primary_key=True)

    # Player id's.
    player_1 = db.Column(db.String())
    player_2 = db.Column(db.String())
    player_3 = db.Column(db.String())
    player_4 = db.Column(db.String())

    # Team scores.
    score_12 = db.Column(db.Integer)
    score_34 = db.Column(db.Integer)

    # Points for all players.
    points_1 = db.Column(db.Integer, default=0)
    points_2 = db.Column(db.Integer, default=0)
    points_3 = db.Column(db.Integer, default=0)
    points_4 = db.Column(db.Integer, default=0)

    # Sinks per player.
    sinks_1 = db.Column(db.Integer, default=0)
    sinks_2 = db.Column(db.Integer, default=0)
    sinks_3 = db.Column(db.Integer, default=0)
    sinks_4 = db.Column(db.Integer, default=0)

    # Timestamp for the match.
    timestamp = db.Column(db.Integer)

    def __init__(self, player_1, player_2, player_3, player_4,
                 score_12, score_34, points, sinks, timestamp, game_id):
        self.player_1 = player_1
        self.player_2 = player_2
        self.player_3 = player_3
        self.player_4 = player_4
        self.points_1, self.points_2, self.points_3, self.points_4 = points
        self.sinks_1, self.sinks_2, self.sinks_3, self.sinks_4 = sinks
        self.score_12 = score_12
        self.score_34 = score_34
        self.timestamp = timestamp
        self.game_id = game_id

    def __repr__(self):
        return f"<id {self.id}>"

    def __team_of_two(self, team):
        """ Will be used when database supports 1 v. 1 matches. """
        return isinstance(team, list) or isinstance(team, tuple)


class Rank(db.Model):
    """ Schema for people and rankings. """
    __tablename__ = 'rankings'
    id = db.Column(db.Integer, primary_key=True)

    # Player information.
    player_id = db.Column(db.String())
    name = db.Column(db.String())
    rank = db.Column(db.Integer)

    # Career stats.
    games = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    sinks = db.Column(db.Integer, default=0)

    def __init__(self, player_id, name, initial_rank):
        self.player_id = player_id
        self.name = name
        self.rank = initial_rank

    def __repr__(self):
        return f"<id {self.id}>"


if __name__ == "__main__":
    app.debug = False
    app.run(host='0.0.0.0')
