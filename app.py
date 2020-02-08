import os
import requests
import commands.groupme_message_type as gm


from flask import Flask, request
from flask_heroku import Heroku
from taunt import taunt
from typing import Any, Dict, List, Tuple
from commands.score import ScoreCommand
from commands.leaderboard import LeaderboardCommand
from commands.add_user import AddCommand
from commands.help import HelpCommand
from commands.models import Score
from commands.refresh import RefreshCommand
from commands.scoreboard import ScoreboardCommand
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from database import db

app = Flask(__name__)

# Used for local testing.
if app.debug:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

# Initializing the app.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
heroku = Heroku(app)
# db = SQLAlchemy(app)
db.init_app(app)
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
    print(message)

    # Ignore messages sent from the bot.
    if sender_is_bot(message):
        return 'ok', 200

    commands = []

    if text.startswith(gm.RECORD_SCORE):
        if sender not in admin:
            commands.append(ScoreCommand(message, check=True))
        else:
            commands.append(ScoreCommand(message))
    elif (text.startswith(gm.LEADERBOARD) or
          text.startswith(gm.LB)):
        commands.append(LeaderboardCommand(message))
    elif (text.startswith(gm.ADMIN_VERIFY)) and sender in admin:
        messages = get_messages_before_id(message.get('id'))
        messages = filter_messages_for_scores(messages)
        for msg in messages:
            commands.append(ScoreCommand(msg))
    elif (text.startswith(gm.HELP_V)):
        commands.append(HelpCommand(message, verbose=True))
    elif (text.startswith(gm.HELP)):
        commands.append(HelpCommand(message))
    elif (text.startswith(gm.ADD_USER)):
        command = AddCommand(message) if sender in admin else\
            AddCommand(message, admin=False)
        commands.append(command)
    elif (text.startswith("/sb")):
        commands.append(ScoreboardCommand(message))
    elif (text.startswith("/refresh")) and sender in admin:
        commands.append(RefreshCommand(message))
    elif gm.BOT_NAME in text.lower():
        note = taunt(message.get('text', ''))
        print(note)
        if not app.debug:
            reply(note)

    for command in commands:
        data = command.generate_data(db)
        note = command.generate_message()
        print(note)

        if not app.debug:
            if data is not None:
                db.session.add(data)
            db.session.commit()
            reply(note)

    return 'ok', 200


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
    msgs: List[str] = []
    last_updated_game = Score.query.order_by(Score.timestamp.desc()).first()
    last_timestamp: int = last_updated_game.timestamp

    for message in messages.get('messages'):
        text = message.get('text', '')
        if text.startswith("/score"):
            timestamp = message.get("created_at")
            favorites = message.get('favorited_by')

            for favorite in favorites:
                if (favorite in admin) and (timestamp > last_timestamp):
                    msgs.append(message)

    return msgs


def sender_is_bot(message):
    return message['sender_type'] == "bot"


if __name__ == "__main__":
    app.debug = False
    app.run(host='0.0.0.0')
