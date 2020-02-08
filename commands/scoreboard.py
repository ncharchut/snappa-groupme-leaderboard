from commands.command import BaseCommand
from commands.models import Stats


class ScoreboardCommand(BaseCommand):
    def __init__(self, message):
        super().__init__(message)

    def generate_data(self, db):
        return None

    def generate_message(self):
        sender: str = self.get_sender()
        if len(self.mentions) == 0:
            return "Must tag 1 other person."

        final_string = ''
        for mention in self.mentions + [sender]:
            name = self.translate(mention)
            if name == '':
                return "One of the tagged is not in the system."
            stats = Stats.query.filter(Stats.name == name).first()
            final_string += (f"{name}: ({stats.wins} - "
                             f"{stats.losses})"
                             f" ELO of {stats.elo}\n")
        return final_string
