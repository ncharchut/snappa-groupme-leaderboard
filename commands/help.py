from commands.command import BaseCommand
from commands import groupme_message_type as gm


class HelpCommand(BaseCommand):
    def __init__(self, message, verbose=False):
        super().__init__(message)
        self.verbose = verbose

    def generate_message(self):
        if self.verbose:
            return gm.HELP_STRING_V
        return gm.HELP_STRING

    def generate_data(self, db):
        return None
