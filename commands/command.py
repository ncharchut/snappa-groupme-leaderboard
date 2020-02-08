from commands.parse import parse_input
import os


class BaseCommand(object):
    def __init__(self, message):
        self.message = message
        self.text = message.get('text', '')
        self.ok, self.parsed = parse_input(self.text)
        self.mentions = self.get_mentions()
        self.timestamp = self.message.get('created_at', None)

    def get_sender(self):
        return self.message.get('sender_id', None)

    def translate(self, raw_id):
        ids = map(lambda x: x.split('%'),
                  (os.environ.get('IDS', '').split(':')))
        convert_dict = {id: name for [id, name] in ids}
        return convert_dict.get(raw_id, '')

    def get_mentions(self):
        attachments = self.message.get('attachments')
        if len(attachments) == 0:
            return []
        return self.message.get('attachments', [{}])[0].get('user_ids', [])

    def generate_message(self):
        raise NotImplementedError("Implement me!")

    def generate_data(self):
        raise NotImplementedError("Implement me!")
