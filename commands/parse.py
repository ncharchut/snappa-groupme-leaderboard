import commands.groupme_message_type as gm
from pyparsing import Word, OneOrMore, Group,\
    Optional, nums, alphanums, Suppress, CaselessKeyword
from pyparsing import pyparsing_common as cmn
from typing import Any, List
import settings


def parse_input(raw_string: str) -> Any:
    command = (Suppress('/') + Word(alphanums).setResultsName('command'))
    mention = Suppress('@') +\
        OneOrMore(Word(alphanums + "'-")).setParseAction(' '.join)\
        .setResultsName('mentions*')

    args_delim = Suppress(',')
    args = OneOrMore(Word(alphanums) + Optional(Suppress('-')))\
        .setResultsName('args')
    total = command + Optional(OneOrMore(mention) + args_delim + args)
    try:
        res: List = total.parseString(raw_string)
        return True, res
    except Exception:
        return False, settings.ERR


def score_parse(raw_string: str) -> Any:
    """
    Parses the given input text as defined below. Returns
    an exception if formatting is not met.

    /score @A [[m1 s1]] @B [[m2 s2]]\
           @C [[m3 s3]] @D [[m4 s4]] SCORE_AB [-,|] SCORE_CD

    Args:
        raw_string [str]: input message from GroupMe.
    Returns:
        [list]: parsed input, if accepted.
        [Exception]: if not accepted.
    """
    init = Suppress(CaselessKeyword(gm.RECORD_SCORE))
    score = Word(nums, max=2).setParseAction(cmn.convertToInteger)
    score_delims = Suppress(Optional(Word("|,-")))
    paren_open = Suppress(Word('[('))
    paren_closed = Suppress(Word('])'))

    # Tagging a user with optional mugs and sinks.
    mention = Suppress('@') +\
        OneOrMore(Word(alphanums)).setParseAction(' '.join)
    points_sinks = Optional(paren_open +
                            Optional(score, default=0) +
                            score_delims +
                            Optional(score, default=0) +
                            paren_closed
                            ).setParseAction(cmn.convertToInteger)
    total_score = score + score_delims + score
    mentions = OneOrMore(Group(mention + points_sinks))

    # Putting it all together.
    score_parse = init +\
        mentions + Suppress(Optional(Word(",|.;/"))) + Group(total_score)
    try:
        res = score_parse.parseString(raw_string)
        return True, res
    except Exception as e:
        print("Failed.")
        return False, e


def add_user(raw_string: str) -> Any:
    init = Suppress(CaselessKeyword(gm.ADD_USER))

    # Tagging a user with optional mugs and sinks.
    mention = Suppress('@' +
                       OneOrMore(Word(alphanums)).setParseAction(' '.join))
    full_name = OneOrMore(Word(alphanums)).setParseAction(' '.join)

    add_user_parse = init + mention + Suppress(',') + full_name

    try:
        res = add_user_parse.parseString(raw_string)
        return True, res
    except Exception as e:
        print("Failed.")
        return False, e


if __name__ == "__main__":
    string = "/add @Pam duke, Pam Duke"
    _, res = parse_input(string)
    print(res.args)
    print(res)
