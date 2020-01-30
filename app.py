import json
import models
import os
import parse
import requests
import settings
import sys
import groupme_message_type as gm


from copy import copy
from flask import Flask, request
from flask_heroku import Heroku
from flask_sqlalchemy import SQLAlchemy
from taunt import taunt
from typing import Any, Dict, List, Set, Tuple
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
Stats = models.create_stats_data_object(db)
init_rank = False

GroupMe = Dict
Response = Tuple[str, int]


@app.route('/', methods=['POST'])
def webhook() -> Response:
    """
    Receives the JSON object representing the GroupMe message, and
    sends a response, if necessary.

    Returns:
        str: 'ok' or 'not ok'.
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
                    else score(message, check=True)
    elif (text.startswith(gm.LEADERBOARD) or
          text.startswith(gm.LB)):
        response = generate_leaderboard()
    elif (text.startswith(gm.ADMIN_VERIFY)) and sender in admin:
        messages = get_messages_before_id(message.get('id'))
        response = filter_messages_for_scores(messages)
    elif (text.startswith(gm.HELP_V)):
        response = gm.HELP_STRING_V
    elif (text.startswith(gm.HELP)):
        response = gm.HELP_STRING
    elif (text.startswith(gm.ADD_USER)):
        response = "Only an admin can add users."\
                if sender not in admin else add_user(message)
    elif (text == "/replay") and sender in admin:
        replay_records()
    elif gm.BOT_NAME in text.lower():
        response = taunt(message.get('text', ''))

    print(message)
    return send_response(response)


def add_user(message: GroupMe) -> str:
    raw_string: str = os.environ.get('IDS', '')
    ids: List[str] = raw_string.split(':')
    current_users: Set[str] = set(map(lambda x: x.split('%')[0], ids))
    mentions = message.get('attachments', [{}])[0].get('user_ids', [])

    if len(mentions) == 0:
        return "No tags detected, try again."

    mentioned: str = mentions[0]
    if mentioned in current_users:
        return "User already added."

    text: str = message.get('text', '')
    (ok, parsed) = parse.add_user(text)
    msg: str = ''
    if not ok:
        msg += "Invalid. Must be `/add @mention, NAME`."
    else:
        full_name: str = parsed[0]
        indata = Stats(mentioned, full_name)
        data = copy(indata.__dict__)
        del data["_sa_instance_state"]
        name_string = mentioned + '%' + full_name
        if not set_config_var('IDS', f"{raw_string}:{name_string}"):
            try:
                db.session.add(indata)
                db.session.commit()
                msg += f"{full_name} added."
            except Exception as e:
                print(f"FAILED entry: {json.dumps(data)}\n")
                print(e)
                sys.stdout.flush()
                return False

    return msg


def set_config_var(var: str, value: Any) -> None:
    url = 'https://api.heroku.com/apps/snappa-groupme-leaderboard/config-vars'
    token = os.environ.get('HEROKU_TOKEN')
    data = {var: value}
    headers = {'Authorization': f"Bearer {token}",
               'Accept': 'application/vnd.heroku+json; version=3',
               'Content-Type': 'application/json'}

    if 'BOT_ID' in requests.patch(url, headers=headers, json=data):
        return True
    return False


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


def score(message: Dict, check: bool = False) -> str:
    """
    Parses a GroupMe message object to verify and log the given match.

    Args:
        message [Dict]: Input GroupMe message JSON.
        check   [bool]: Flag indicating whether an admin is verifying
                        or sending the score directly.

    Returns:
        str: The bot's response to the input.
    """
    text: str = message.get('text', '')
    (ok, parsed) = parse.score_parse(text)
    msg: str = ''
    if not ok:
        if check:
            msg += 'Bad command: \n'
            msg += text
        msg += gm.ERROR_STRING
    else:
        db_data, note = _process_data_for_db(parsed, message)
        players = db_data[:4]
        if len(players) == 0:
            msg += note
        else:
            add_to_db(db, *db_data)
            msg += match_string(db_data)
            if len(note) > 0:
                msg += "-------------------------\n"
                msg += note

    return msg


def match_string(db_data) -> str:
    """ Generates the string describing the given match. """
    player_1, player_2, player_3, player_4,\
        score_12, score_34, _, _, _, elo_1, elo_2, elo_3, elo_4 = db_data
    return (f"Match recorded, score of {score_12} - {score_34}.\n"
            "-------------------------\n"
            f"{'W: ' if score_12 > score_34 else 'L: '}"
            f"{player_name(player_1)}, {player_name(player_2)}\n"
            f"{'W: ' if score_34 > score_12 else 'L: '}"
            f"{player_name(player_3)}, {player_name(player_4)}\n")


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
    elos: List[Stats] = Stats.query.order_by(Stats.elo).limit(15)
    msg: str = 'LEADERBOARD\n'.rjust(10)
    msg += '-------------------------\n'

    for player in elos:
        name: str = player.name
        elo: int = player.elo
        msg += f"{elo}   -   {name}\n"

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
    parsed = parsed
    players = [list(parsed[i]) for i in range(4)]
    score_12, score_34 = list(parsed[-1])

    player_names = list(map(lambda x: x[0], players))
    player_1, player_2, player_3, player_4 = player_names

    stats: List[Stats] = Stats.query.filter((Stats.name == player_1) |
                                            (Stats.name == player_2) |
                                            (Stats.name == player_3) |
                                            (Stats.name == player_4)).all()

    elo_1, elo_2, elo_3, elo_4 = calculate_elo(stats, score_12, score_34)

    points = list(map(lambda x: 0 if len(x) == 1 else x[1], players))
    sinks = list(map(lambda x: 0 if len(x) == 1 else x[2], players))
    note: str = ''
    db_data: List = []

    # Error checking.
    if max(score_12, score_34) < settings.MIN_SCORE_TO_WIN:
        note = "Games to less than 7 are for the weak. Disregarded."

    if abs(score_12 - score_34) < settings.WIN_BY:
        note = f"It's win by {settings.WIN_BY}, numbnut."

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

    for player in range(settings.NUM_PLAYERS):
        if points[player] < sinks[player]:
            note = (f"I don't know how {players[player][0]} sunk more "
                    "times than scored, but I'm impressed.")

    if len(note) == 0:
        db_data = [player_1, player_2, player_3, player_4, score_12,
                   score_34, points, sinks, timestamp,
                   elo_1, elo_2, elo_3, elo_4]
        if abs(score_12 - score_34) > settings.MERCY_THRESHOLD:
            note = "I smell a naked lap coming."

    return db_data, note


def calculate_elo(stats: Stats, score_a, score_b):
    elo_1, elo_2, elo_3, elo_4 = list(map(lambda x: x.elo, stats))
    team_a_avg = 0.5 * (elo_1 + elo_2)
    team_b_avg = 0.5 * (elo_3 + elo_4)
    expected_a = 1 / (1 + 10 ** ((team_b_avg - team_a_avg) / 500))
    expected_b = 1 / (1 + 10 ** ((team_a_avg - team_b_avg) / 500))
    score_p_a = score_a / (score_a + score_b)
    score_p_b = 1 - score_p_a

    elo_delta_a = settings.K * (score_p_a - expected_a)
    elo_delta_b = settings.K * (score_p_b - expected_b)

    return (elo_1 + elo_delta_a, elo_2 + elo_delta_a,
            elo_3 + elo_delta_b, elo_4 + elo_delta_b)


def replay_records():
    records = Score.query.order_by(Score.timestamp).all()
    n_records = len(records)
    stats = Stats.query.all()
    stats_dict = {stat.name: stat for stat in stats}

    for j, record in enumerate(records):
        for i, player in enumerate([record.player_1,
                                    record.player_2,
                                    record.player_3,
                                    record.player_4]):
            player_stat = stats_dict[player]
            update_player_stats(player_stat, i, record)
        # Update future elo, so things work out.
        if j < (n_records - 1):
            future_record = records[j + 1]
            future_record.elo_1 = player_stat.elo_1
            future_record.elo_2 = player_stat.elo_2
            future_record.elo_3 = player_stat.elo_3
            future_record.elo_4 = player_stat.elo_4

    if app.debug:
        for record in records:
            print(record)
            print(stats)
    else:
        db.session.commit()


def update_player_stats(player, player_number, record):
    player.games = Stats.games + 1
    points = [record.points_1, record.points_2,
              record.points_3, record.points_4]
    sinks = [record.sinks_1, record.sinks_2,
             record.sinks_3, record.sinks_4]
    elos = [record.elo_1, record.elo_2,
            record.elo_3, record.elo_4]
    if record.score_12 > record.score_34:
        if player_number in [1, 2]:
            player.wins = Stats.wins + 1
        else:
            player.losses = Stats.losses + 1
    player.points = Stats.points + points[player_number]
    player.sinks = Stats.sinks + sinks[player_number]
    player.elo = elos[player_number]


def add_to_db(db: Any,
              player_1: str, player_2: str, player_3: str, player_4: str,
              score_12: int, score_34: int, points: int, sinks: int,
              timestamp: int, elo_1: int, elo_2: int, elo_3: int,
              elo_4: int) -> bool:
    """ Given the necessary data entries, logs game score to database. """
    indata: Score = Score(player_1, player_2, player_3, player_4,
                          score_12, score_34, points, sinks, timestamp,
                          elo_1, elo_2, elo_3, elo_4)
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
        indata = Stats(groupme_id, name)
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
              'limit': 20}

    msg_rqst = requests.get(url, params=params)
    return msg_rqst.json()['response']


def filter_messages_for_scores(messages: Dict) -> List[str]:
    """
    Filters a GroupMe JSON object for all attached messages, computes
    score strings and adds them to the database.
    """
    admin: List[str] = os.getenv('ADMIN').split(':')
    msgs: List[str] = []
    last_updated_game = Score.query.order_by(Score.timestamp.desc()).first()
    last_timestamp: int = last_updated_game.timestamp

    for message in messages.get('messages'):
        text = message.get('text')
        if text.startswith("/score"):
            timestamp = message.get("created_at")
            favorites = message.get('favorited_by')

            for favorite in favorites:
                if (favorite in admin) and (timestamp > last_timestamp):
                    msgs.append(score(message, check=True))

    if len(msgs) == 0:
        msgs.append("Chill homie, we're already updated.")

    return msgs


# Checks whether the message sender is a bot
def sender_is_bot(message):
    return message['sender_type'] == "bot"


if __name__ == "__main__":
    app.debug = False
    app.run(host='0.0.0.0')
