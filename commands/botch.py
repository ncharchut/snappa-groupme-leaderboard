import os
import requests

from commands.command import BaseCommand
from commands import settings
from typing import Any
from commands.models import Stats


class BotchCommand(BaseCommand):
    def __init__(self, message, unbotch=False, admin=True):
        super().__init__(message)
        self.note = ''
        self.admin = admin
        self.unbotch = unbotch

    def set_config_var(self, var: str, value: Any) -> None:
        url = settings.URL
        token = os.environ.get('HRKU_TOKEN')
        data = {var: value}
        headers = {'Authorization': f"Bearer {token}",
                   'Accept': 'application/vnd.heroku+json; version=3',
                   'Content-Type': 'application/json'}

        # This denotes a successful request.
        response = requests.patch(url, headers=headers, json=data)
        return response.status_code == 200

    def generate_message(self):
        if not self.admin:
            return "Only an admin can botch users."
        return self.note

    def generate_data(self, db):
        if not self.admin:
            return None

        if len(self.mentions) == 0:
            self.note = "No tags detected, try again."
            return None

        mentioned: str = self.mentions[0]
        mentioned_name = self.translate(mentioned)

        if len(mentioned_name) == 0:
            self.note = "Must add user before botching."
            return None

        reason = ' '.join(self.parsed.args)
        if len(reason) == 0:
            self.note = "Must include reason for botching."
            return

        stat = Stats.query.filter(Stats.name == mentioned_name).first()
        sign = -1 if self.unbotch else 1
        stat.elo -= sign * 10
        botch_str = "BOTCH" if not self.unbotch else "UNBOTCH"
        self.note = (f"{botch_str} {mentioned_name} "
                     f"({stat.elo + sign * 10:.0f} -> "
                     f"{stat.elo:.0f}) for:\n\n{reason}.")

        return stat
