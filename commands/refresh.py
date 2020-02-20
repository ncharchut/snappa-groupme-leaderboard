from commands.models import Score, Stats
from commands.leaderboard import LeaderboardCommand
from commands import settings
from typing import List
import numpy as np
import csv


class RefreshCommand(LeaderboardCommand):
    def __init__(self, message):
        super().__init__(message)

    def generate_message(self):
        return "Leaderboard refreshed.\n\n" +\
                self.generate_leaderboard()

    def load_prerankings(self):
        file = "resources/prerankings.csv"
        name_dict = {}
        with open(file, 'r') as read_file:
            reader = csv.reader(read_file)
            for ranking in reader:
                elo = ranking[0]
                for name in ranking[1:]:
                    name_dict[name] = elo

        return name_dict

    def clean_stats(self, db):
        all_stats = Stats.query.all()
        elo_dict = self.load_prerankings()
        for stat in all_stats:
            name = stat.name
            stat.elo = elo_dict.get(name, 1000)
            stat.wins = 0
            stat.losses = 0
            stat.games = 0

        for record in Score.query.all():
            record.elo_1 = 1000
            record.elo_2 = 1000
            record.elo_3 = 1000
            record.elo_4 = 1000

        db.session.commit()
        # REMOVE AFTER DEBUGGING
        for record in Stats.query.order_by(Stats.name).all():
            print(record)

    def calculate_elo(self, stats: List, score_a, score_b):
        """
        Calculates updated elo ratings for the players involved in the match.
        """
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
        return (elo_1 + elo_delta, elo_2 + elo_delta,
                elo_3 - elo_delta, elo_4 - elo_delta)

    def generate_data(self, db):
        records = Score.query.order_by(Score.timestamp).all()
        n_records = len(records)
        self.clean_stats(db)

        for j in range(n_records):
            record = records[j]
            # print(f"Updating: {record}")
            stats = Stats.query.all()
            stats_dict = {stat.name: stat for stat in stats}
            stats = [stats_dict[record.player_1],
                     stats_dict[record.player_2],
                     stats_dict[record.player_3],
                     stats_dict[record.player_4]]
            elos = self.calculate_elo(stats, record.score_12,
                                      record.score_34)

            # Update game records.
            record.elo_1 = elos[0]
            record.elo_2 = elos[1]
            record.elo_3 = elos[2]
            record.elo_4 = elos[3]

            # Update stats for each player in the match.
            score_12, score_34 = record.score_12, record.score_34
            win_losses = [1, 1, 0, 0] if score_12 > score_34\
                else [0, 0, 1, 1]

            for player, elo, win_loss in zip(stats, elos, win_losses):
                player.games = Stats.games + 1
                if win_loss == 1:
                    player.wins = Stats.wins + 1
                else:
                    player.losses = Stats.losses + 1
                player.elo = elo
                db.session.commit()

            print(f"Updated: {record}")
        return None
