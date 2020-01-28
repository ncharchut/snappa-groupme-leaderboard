import csv
import json
import models
import os
import parse
import random
import requests
import sys
import groupme_message_type as gm


from copy import copy
from flask import Flask, request
from flask_heroku import Heroku
from flask_sqlalchemy import SQLAlchemy
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

Response = Tuple[str, int]


@app.route('/', methods=['POST'])
def webhook() -> Response:
    """
    Receives the JSON object representing the GroupMe message, and
    sends a response, if necessary.

    Returns:
        str: 'ok' or 'not ok'.
        int: Standard error code.
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

    response: str = ''
    if text.startswith(gm.RECORD_SCORE):
        response = "Waiting for approval." if sender not in admin\
                    else score(message)
    elif (text.startswith(gm.LEADERBOARD) or
          text.startswith(gm.LB)):
        response = generate_leaderboard()
    elif (text.startswith(gm.ADMIN_VERIFY)) and sender in admin:
        messages = get_messages_before_id(message.get('id'))
        response = filter_messages_for_scores(messages)
    elif (text.startswith(gm.HELP)):
        response = gm.HELP_STRING
    elif gm.BOT_NAME in text.lower():
        response = taunt(message.get('text', ''))

    return send_response(response)


def send_response(response: Any) -> Response:
    """
    Sends the bot's response to the GroupMe API.

    Args:
        response [str]: The bot's determined response.

    Returns:
        str: 'ok' or 'not ok'.
        int: Standard error code.
    """

    if not app.debug:
        if isinstance(response, list):
            for msg in response:
                reply(msg)
        elif response != '':
            reply(response)
    print(response)
    return 'ok', 200


def taunt(text: str) -> str:
    """
    Generates a taunt or corresponding response to messages
    that are directed at the bot.

    Args:
        text [str]: The text of the incoming GroupMe message.

    Returns:
        str: An emotional response from its phrase repository.
    """
    blob = TextBlob(text)
    polarity, subjectivity = blob.sentiment
    sentiment = gm.Sentiment.NEUTRAL
    if polarity < -0.3:
        sentiment = gm.Sentiment.BAD
    elif polarity > 0.3:
        sentiment = gm.Sentiment.GOOD
    return get_emotional_response(sentiment)


def get_emotional_response(sentiment: gm.Sentiment) -> str:
    """
    Generates an emotional response of the given sentiment.

    Args:
        sentiment [Sentiment]: Enum describing message sentiment.

    Returns:
        str: Chosen respnose to the identified sentiment.
    """
    level: str = sentiment.name.lower()
    file = f"resources/responses/{level}.csv"
    response = ''
    with open(file, 'r') as responses:
        reader = list(csv.reader(responses))
        response = random.choice(reader)[0]

    return response


def score(message: Dict) -> str:
    """
    Parses a GroupMe message object to verify and log the given match.

    Args:
        message [Dict]: Input GroupMe message JSON.

    Returns:
        str: The bot's response to the input.
    """
    text: str = message.get('text', '')
    (ok, parsed) = parse.score_parse(text)
    msg: str = ''
    if not ok:
        msg += gm.ERROR_STRING
    else:
        db_data, note = _process_data_for_db(parsed, message)
        players = db_data[:4]
        if len(players) == 0:
            msg += note
        else:
            add_to_db(*db_data)
            msg += match_string(db_data)
            if len(note) > 0:
                msg += "-------------------------\n"
                msg += note

    return msg


def match_string(db_data) -> str:
    """ Generates the string describing the given match. """
    player_1, player_2, player_3, player_4,\
        score_12, score_34, _, _, _ = db_data
    return (f"Match recorded:\n"
            f"{player_name(player_1)}, {player_name(player_2)}"
            f"{'(W)' if score_12 > score_34 else '(L)'}"
            f" v. {player_name(player_3)}"
            f", {player_name(player_4)}"
            f"{'(W)' if score_34 > score_12 else '(L)'}"
            f" | {score_12} - {score_34}\n")


def player_name(player) -> str:
    """ Given a player's name, returns their first name and last initial. """
    names = player.split(' ')
    first: str = names[0]
    last_initial: str = names[-1][0] + '.'
    return ' '.join([first, last_initial])


def generate_leaderboard() -> str:
    """
    Generates and returns the leaderboard string by querying the database.
    """
    ranks: List[Rank] = Rank.query.order_by(Rank.name).limit(10)
    msg: str = 'LEADERBOARD\n'.rjust(10)
    msg += '-------------------------\n'

    for player in ranks:
        name: str = player.name
        rank: int = player.rank
        msg += f"{rank}   -   {name}\n"

    return msg


def _process_data_for_db(parsed: List[Any], message: Dict) -> Tuple[List, str]:
    """
    Given a parsed message string, further processes the data
    to be added to the database. Also, conduct some post-processing
    error-checking.

    Args:
        parsed [List[Any]]: The parsed input string, per `parse.score_parse`.
        message [Dict]: Input GroupMe message JSON.

    Returns:
        Tuple[List, str]: Processed data ready for entry to database, alone
                          with additional string response from the bot,
                          if necessary.
    """
    # Generate converting dictionary to replace sender names with real names.
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
        db_data = [player_1, player_2, player_3, player_4, score_12,
                   score_34, points, sinks, timestamp]
        if abs(score_12 - score_34) > 4:
            note = "I smell a naked lap coming."

    return db_data, note


def add_to_db(player_1: str, player_2: str, player_3: str, player_4: str,
              score_12: int, score_34: int, points: int, sinks: int,
              timestamp: int) -> bool:
    """ Given the necessary data entries, logs game score to database. """
    indata: Score = Score(player_1, player_2, player_3, player_4,
                          score_12, score_34, points, sinks, timestamp)
    data: Dict = copy(indata.__dict__)
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


def __init_rankings() -> bool:
    """
    Uses a csv file of GroupMe IDs to real names to initialize
    the database.
    """
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


def reply(msg: str) -> None:
    """ Sends the bot's message via the GroupMe API. """
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


def get_messages_before_id(before_id: str) -> Dict:
    """
    Retrieves the 10 previous messages to the message
    with id equal to `before_id`.
    """
    group_id = os.environ.get('GROUPME_GROUP_ID')
    token = os.environ.get('ACCESS_TOKEN')
    url = f'https://api.groupme.com/v3/groups/{group_id}/messages'
    params = {'before_id': str(before_id),
              'token': token,
              'limit': 10}

    msg_rqst = requests.get(url, params=params)
    return msg_rqst.json()['response']


def filter_messages_for_scores(messages: Dict) -> List[str]:
    """
    Filters a GroupMe JSON object for all attached messages, computes
    score strings and adds them to the database.
    """
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


# Checks whether the message sender is a bot
def sender_is_bot(message):
    return message['sender_type'] == "bot"


if __name__ == "__main__":
    app.debug = False
    app.run(host='0.0.0.0')
