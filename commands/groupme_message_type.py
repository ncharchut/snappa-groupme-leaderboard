from enum import Enum


class Sentiment(Enum):
    BAD = 1
    NEUTRAL = 2
    GOOD = 3


ERROR_STRING = ("Invalid. "
                "Must be `/score @A @B @C @D, SCORE_AB - SCORE_CD` or\n"
                "`/score @A (p1 s1) @B (p2 s2)"
                " @C (p3 s3) @D (p4 s4), SCORE_AB - SCORE_CD`")

HELP_STRING_V = ("Sup, bitches. It's ScoreBot. Here's the lowdown.\n\n"
                 "Anyone can send a score, but an admin has to"
                 " like their message and send `/check` to the GroupMe"
                 " before I can officially record the match. Obviously,"
                 " admins do not need my approval."
                 " Check this chat's topic to see who they are!\n\n"
                 "To score a match: \n"
                 "`/score @A @B @C @D, SCORE_AB - SCORE_CD` or\n"
                 "\t`/score @A (p1 s1) @B (p2 s2)`"
                 " @C (p3 s3) @D (p4 s4), SCORE_AB - SCORE_CD`\n\n"
                 "Note a couple things here. One, if you log player points"
                 " (the `p`s above; optional), you must do it for both"
                 " people on the team. The same doesn't apply for sinks"
                 " (the `s`s; also optional), since I'll assume you won't sink"
                 " shit. You must also include the brackets/parens.\n\n"
                 "To see the leaderboard (currently meaningless):\n"
                 "`/leaderboard` or `/lb`\n\n"
                 "To get help:\n"
                 "`/help` or `/helpv` for verbose help.\n\n"
                 "Games must be to 7, win by 2, drinking thirds, no questions."
                 " That's all from me, let's toss some dye.")

HELP_STRING = (f"To score a match: \n"
               "`/score @A @B @C @D, SCORE_AB - SCORE_CD` or\n"
               "\t`/score @A (p1 s1) @B (p2 s2)`"
               " @C (p3 s3) @D (p4 s4), SCORE_AB - SCORE_CD`\n\n"
               "Note a couple things here. One, if you log player points"
               " (the `p`s above; optional), you must do it for both"
               " people on the team. The same doesn't apply for sinks"
               " (the `s`s; also optional), since I'll assume you won't sink"
               " shit. You must also include the brackets/parens.\n\n"
               "To see the leaderboard (currently meaningless):\n"
               "`/leaderboard` or `/lb`\n\n"
               "To get help:\n"
               "`/help` or `/helpv` for verbose help.\n\n"
               " Games must be to 7, win by 2, drinking thirds, no questions."
               " Let's toss some dye.")

# Constants for the names of the various commands.
ADD_USER = "/add"
ADMIN_VERIFY = "/check"
BOT_NAME = "scorebot"
HELP = "/help"
HELP_V = "/helpv"
LB = "/lb"
LEADERBOARD = "/leaderboard"
RECORD_SCORE = "/score"
