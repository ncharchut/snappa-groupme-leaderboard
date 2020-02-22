import os
import numpy as np
from commands import settings

from commands.command import BaseCommand
from commands.models import Stats, Score
from typing import List


class ScoreCommand(BaseCommand):
    cmd = settings.SCORE_CMD

    def __init__(self, message, check=False):
        super().__init__(message)
        self.invalid = False
        self.players = self.get_players()
        self.scores = self.get_scores()
        self.check = check
        self.elo_delta = 0

    def get_players(self):
        if not self.ok:
            return

        if (len(self.parsed.mentions) > settings.NUM_PLAYERS or
                len(self.parsed.mentions) < settings.NUM_PLAYERS - 1):
            self.invalid = True
            return

        ids = map(lambda x: x.split('%'),
                  (os.environ.get('IDS', '').split(':')))
        convert_dict = {id: name for [id, name] in ids}
        convert_dict['me'] = convert_dict.get(self.get_sender(), '')
        for i in range(settings.NUM_PLAYERS):
            player = self.parsed.mentions[i]
            if player == "me":
                self.mentions.insert(i, self.get_sender())

        players = [convert_dict.get(id, None) for id in self.mentions]

        if None in players or len(players) != settings.NUM_PLAYERS:
            self.invalid = True

        return players

    def get_scores(self):
        if not self.ok:
            return
        return list(map(int, self.parsed.args))

    def calculate_elo(self, stats: List):
        """
        Calculates updated elo ratings for the players involved in the match.
        """
        score_a, score_b = self.scores
        elo_1, elo_2, elo_3, elo_4 = list(map(lambda x: x.elo, stats))
        games_1, games_2, games_3, games_4 = \
            list(map(lambda x: x.games, stats))

        # Teams are considered as single players, averaging their Elo.
        team_a_avg = 0.5 * (elo_1 + elo_2)
        team_b_avg = 0.5 * (elo_3 + elo_4)
        expected_a = 1 / (1 + 10 ** ((team_b_avg - team_a_avg) / 400))

        # Win probability is the # points a team scorse divided by the total.
        score_diff = abs(score_a - score_b)
        mult = 1
        lose_a = score_a < score_b

        # K-factor multiplier to account for larger margins.
        # 7-3, 7-4, 7-5
        if 2 <= score_diff <= 4 and (max(score_a, score_b) >
                                     settings.MIN_SCORE_TO_WIN):
            mult = 1.25
            score_a = score_a if not lose_a else 5
            score_b = score_b if lose_a else 5
        # 7-1, 7-2
        elif 5 <= score_diff <= 6:
            mult = 1.75
            score_a = score_a if not lose_a else 2
            score_b = score_b if lose_a else 2
        # 7-0
        elif score_diff == 7:
            mult = 2

        score_p_a = score_a / (score_a + score_b)

        games_12 = 0.5 * (games_1 + games_2)
        games_34 = 0.5 * (games_3 + games_4)
        game_mult = 1 / (1 + np.exp(-max(1, min(games_12, games_34)) /
                                    max(1, max(games_12, games_34))))
        game_mult = 1 if games_12 >= 20 and games_34 >= 20 else game_mult

        elo_delta = game_mult * mult * settings.K * (score_p_a - expected_a)
        self.elo_delta = elo_delta
        return (elo_1 + elo_delta, elo_2 + elo_delta,
                elo_3 - elo_delta, elo_4 - elo_delta)

    def generate_message(self):
        if not self.ok:
            return (("Must be of form:\n /score @A @B @C @D, "
                     "score_ab - score_cd"))

        if self.invalid:
            return ("Error processing. Likely someone isn't added, or"
                    " format isn't correct. Try `/help` if you're uncertain.")

        if self.check:
            return "Waiting for approval."

        score_1, score_2 = self.scores
        if max(score_1, score_2) < settings.MIN_SCORE_TO_WIN:
            return (f"Games to less than {settings.MIN_SCORE_TO_WIN} "
                    "are for the weak. Disregarded.")
        elif abs(score_1 - score_2) < settings.WIN_BY:
            return f"It's win by {settings.WIN_BY}, numbnut."

        player_1, player_2, player_3, player_4 = self.players
        negative = self.elo_delta < 0
        self.elo_delta = abs(self.elo_delta)

        sign_1 = '-' if negative else '+'
        sign_2 = '+' if negative else '-'
        d_1 = f"{sign_1}{self.elo_delta:.04}"
        d_2 = f"{sign_2}{self.elo_delta:.04}"
        win_1 = f"W: {d_1}  "
        lose_1 = f"L: {d_1}  "
        win_2 = f"W: {d_2}  "
        lose_2 = f"L: {d_2}  "
        msg: str = (f"Match recorded, score of {score_1} - {score_2}.\n"
                    "-------------------------\n"
                    f"{win_1 if score_1 > score_2 else lose_1}"
                    f"{player_1}, {player_2}\n"
                    f"{win_2 if score_2 > score_1 else lose_2}"
                    f"{player_3}, {player_4}\n"
                    "-------------------------\n")

        if abs(score_1 - score_2) > settings.MERCY_THRESHOLD:
            msg += "I smell a naked lap coming."

        return msg

    def generate_data(self, db):
        if (not self.ok) or self.check or self.invalid:
            return None

        # Read in current stats, calculate elo, update current rankings.
        stats = [Stats.query.filter(Stats.name == player).first()
                 for player in self.players]
        updated_elos = self.calculate_elo(stats)

        # Not recording personal stats like this for now.
        new_scores = Score(*self.players, *self.scores,
                           self.timestamp, *updated_elos)

        # Update player stats.
        score_1, score_2 = self.scores
        win_losses = [1, 1, 0, 0] if score_1 > score_2 else [0, 0, 1, 1]
        for player, elo, win_loss in zip(stats, updated_elos, win_losses):
            player.games = Stats.games + 1
            if win_loss == 1:
                player.wins = Stats.wins + 1
            else:
                player.losses = Stats.losses + 1
            player.elo = elo

        return new_scores


if __name__ == "__main__":
    score = ScoreCommand({"text": "/score @bo @me @tommy @you, 6 - 7",
                          "sender_id": "28847341",
                          "attachments": [{"user_ids":
                                           ["41282369", "46988593",
                                            "18930468"]}]})
    print(score.generate_message())
