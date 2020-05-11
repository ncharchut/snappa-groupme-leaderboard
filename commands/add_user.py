import os
import requests

from commands.command import BaseCommand
from commands import settings
from typing import Any
from commands.models import Stats


class AddCommand(BaseCommand):
    def __init__(self, message, admin=True):
        super().__init__(message)
        self.note = ''
        self.admin = admin

    def set_config_var(self, var: str, value: Any) -> None:
        url = settings.URL
        token = os.environ.get('HRKU_TOKEN')
        data = {var: value}
        headers = {'Authorization': f"Bearer {token}",
                   'Accept': 'application/vnd.heroku+json; version=3',
                   'Content-Type': 'application/json'}

        response = requests.patch(url, headers=headers, json=data)
        return response.status_code == 200

    def generate_message(self):
        if not self.admin:
            return "Only an admin can add users."
        return self.note

    def generate_data(self, db):
        if not self.admin:
            return None

        raw_string: str = os.environ.get('IDS', '')
        self_add = False
        if len(self.mentions) == 0:
            if (len(self.parsed.mentions) > 0) and\
                    (self.parsed.mentions[0] == 'me'):
                self_add = True
            else:
                self.note = "No tags detected, try again."
                return None

        mentioned: str = self.get_sender() if self_add else self.mentions[0]
        names = set([stat.name for stat in Stats.query.all()])
        if mentioned in names:
            self.note = "User already added."
            return None

        full_name: str = ' '.join(self.parsed.args)
        indata = Stats(mentioned, full_name)
        name_string = mentioned + '%' + full_name
        print(raw_string)
        if not self.set_config_var('IDS', f"{raw_string}:{name_string}"):
            self.note = "Request to update users failed."
            return None
        self.note = f"User {full_name} added."
        return indata
