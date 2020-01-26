from pyparsing import Word, OneOrMore, Group,\
    Optional, nums, alphanums, Suppress, CaselessKeyword
from pyparsing import pyparsing_common as cmn


def score_parse(raw_string):
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
    SCORE_COMMAND: str = "/score"

    init = Suppress(CaselessKeyword(SCORE_COMMAND))
    score = Word(nums, max=2).setParseAction(cmn.convertToInteger)
    score_delims = Suppress(Optional(Word("|,-")))

    # Tagging a user with optional mugs and sinks.
    mention = Suppress('@') +\
        OneOrMore(Word(alphanums)).setParseAction(' '.join)
    total_score = score + score_delims + score
    mugs_sinks = Optional(Suppress('[') +
                          total_score +
                          Suppress(']')).setParseAction(cmn.convertToInteger)
    mentions = OneOrMore(Group(mention + mugs_sinks))

    # Putting it all together.
    score_parse = init +\
        mentions + Suppress(Optional(Word(",|"))) + Group(total_score)
    try:
        res = score_parse.parseString(raw_string)
        return True, res
    except Exception as e:
        print("Failed.")
        return False, e


if __name__ == "__main__":
    string = "/sCoRe @tommy long cock [4 5] @bo [4 3] @me @you [3-5] 6 7"
    # string = "/score @Zack Klopstein [3-0] @Tommy Shannan @me [1 2] @Bo Hardon 3  7"
    _, res = score_parse(string)
    print(res)
