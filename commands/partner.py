from commands.command import BaseCommand
from commands.models import Score


class PartnerCommand(BaseCommand):
    def __init__(self, message):
        super().__init__(message)

    def generate_message(self):
        if len(self.mentions) != 1:
            return "Tag one and only one person."

        sender = self.translate(self.get_sender())
        tagged = self.translate(self.mentions[0])

        pair = set([sender, tagged])
        records = Score.query.filter((Score.player_1 == sender) |
                                     (Score.player_1 == tagged) |
                                     (Score.player_2 == sender) |
                                     (Score.player_2 == tagged) |
                                     (Score.player_3 == sender) |
                                     (Score.player_3 == tagged) |
                                     (Score.player_4 == sender) |
                                     (Score.player_4 == tagged)
                                     ).order_by(Score.timestamp).all()
        sender_only = [game for game in records if sender in
                       [game.player_1, game.player_2,
                        game.player_3, game.player_4]]
        tagged_only = [game for game in records if tagged in
                       [game.player_1, game.player_2,
                        game.player_3, game.player_4]]
        sender_only = [game for game in sender_only if tagged not in
                       [game.player_1, game.player_2,
                        game.player_3, game.player_4]]

        tagged_only = [game for game in tagged_only if sender not in
                       [game.player_1, game.player_2,
                        game.player_3, game.player_4]]

        result_dict = {sender: 0, tagged: 0}
        wins = 0
        losses = 0

        last_sender_elo = None
        last_tagged_elo = None
        for idx, game in enumerate(records):
            team_1 = set([game.player_1, game.player_2])
            team_2 = set([game.player_3, game.player_4])

            if game in sender_only:
                last_sender_elo = self.get_elo(game, sender)
            elif game in tagged_only:
                last_tagged_elo = self.get_elo(game, tagged)
            elif not (team_1 == pair or team_2 == pair):
                last_sender_elo = self.get_elo(game, sender)
                last_tagged_elo = self.get_elo(game, tagged)
            else:
                last_sender_elo = 1000 if last_sender_elo is None\
                    else last_sender_elo
                last_tagged_elo = 1000 if last_tagged_elo is None\
                    else last_tagged_elo

                current_sender_elo = self.get_elo(game, sender)
                current_tagged_elo = self.get_elo(game, tagged)

                win = self.check_win(game, pair)
                wins += 1 * win
                losses += 1 * (not win)
                result_dict[sender] += (current_sender_elo - last_sender_elo)
                result_dict[tagged] += (current_tagged_elo - last_tagged_elo)
                last_sender_elo = current_sender_elo
                last_tagged_elo = current_tagged_elo

        res = result_dict[sender]

        return (f"{sender}, {tagged}\n"
                f"W-L: ({wins} - {losses}), ELO: {'+' if res> 0 else ''}{res}")

    def check_win(self, game, pair):
        if set([game.player_1, game.player_2]) == pair:
            return game.score_12 > game.score_34
        elif set([game.player_3, game.player_4]) == pair:
            return game.score_12 < game.score_34
        raise RuntimeError("Shouldn't get here!")

    def get_elo(self, game, player):
        if game.player_1 == player:
            return game.elo_1
        elif game.player_2 == player:
            return game.elo_2
        elif game.player_3 == player:
            return game.elo_3
        elif game.player_4 == player:
            return game.elo_4
        raise RuntimeError(f"Shouldn't get here! \ngame: {game}")

    def generate_data(self, db):
        return
