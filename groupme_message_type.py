from enum import Enum


class MessageType(Enum):
    ADMIN_SCORE = 1
    NON_ADMIN_SCORE = 2
    LEADERBOARD = 3
    ADMIN_VERIFY = 4
    TAUNTING = 5
    NOTHING = 6
    HELP = 7


ERROR_STRING = ("Invalid. "
                "Must be `/score @A @B [@C @D] score1-score2` or\n"
                "`/score @A [p1 s1] @B [p2 s2]"
                "@C [p3 s3] @D [p4 s4] SCORE_AB , SCORE_CD")

HELP_STRING = ("Yo, yo! It's ScoreBot. Here's the lowdown.\n\n"
               "To send a score, you have to be an admin. "
               "Check this chat's topic to see who they are.\n\n"
               "To score a match: \n"
               "`/score @A @B [@C @D] score1-score2` or\n"
               "\t`/score @A [p1 s1] @B [p2 s2]`"
               " @C [p3 s3] @D [p4 s4], SCORE_AB - SCORE_CD`\n\n"
               "Note a couple things here. One, if you log player points"
               " (optional), you must do it for both people on the team."
               "  You must also include the brackets.\n\n"
               "To see the leaderboard (currently meaningless):\n"
               "`/leaderboard` or `/lb`\n\n"
               "Games must be to 7, drinking thirds, no questions. "
               "That's all from me, let's toss some dye.")
