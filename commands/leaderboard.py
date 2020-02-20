from commands.command import BaseCommand
from commands.models import Stats
from commands.settings import LEADERBOARD_DISPLAY, LEADERBOARD_GAMES
from typing import List


class LeaderboardCommand(BaseCommand):
    def __init__(self, message):
        super().__init__(message)

    def generate_message(self):
        """
        Generates and returns the leaderboard string by querying the database.
        """
        return self.generate_leaderboard()

    def generate_leaderboard(self):
        elos: List[Stats] = Stats.query.filter(Stats.games >
                                               LEADERBOARD_GAMES)\
            .order_by(Stats.elo.desc()).limit(LEADERBOARD_DISPLAY)
        msg: str = 'LEADERBOARD\n'.rjust(10)
        msg += '-------------------------\n'

        for player in elos:
            name: str = player.name
            elo_str: str = f"{player.elo:.0f}"
            msg += (f"{elo_str.rjust(4)}   -   {name}   ({player.wins} -"
                    f" {player.losses})\n")

        return msg

    def generate_data(self, db):
        """ Leaderboard does not alter database. """
        return None
