import csv
import random
import commands.groupme_message_type as gm
from textblob import TextBlob


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
