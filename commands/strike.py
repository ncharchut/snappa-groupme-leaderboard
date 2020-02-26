from commands.command import BaseCommand
from commands.models import Score


class StrikeCommand(BaseCommand):
    def __init__(self, message, admin=True):
        super().__init__(message)
        self.admin = admin
        self.note = "That match doesn't exist in the database."

    def generate_data(self, db):
        if not self.admin:
            self.note = "Must be an admin to strike matches."
            return

        match_id = self.parsed.args[0]
        match = Score.query.filter(Score.id == match_id).first()

        if match is None:
            return
        else:
            self.note = (f"Match {match_id} deleted.\n"
                         f"{match.player_1} and {match.player_2} v. "
                         f"{match.player_3} and {match.player_4}, "
                         f"{match.score_12} - {match.score_34}")
            db.session.delete(match)
            db.session.commit()
        return None

    def generate_message(self):
        return self.note

