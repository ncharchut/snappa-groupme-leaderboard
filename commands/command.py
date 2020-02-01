from commands.parse import parse_input


class BaseCommand(object):
    def __init__(self, message):
        self.message = message
        self.text = message.get('text', '')
        self.ok, self.parsed = parse_input(self.text.lower())
        self.mentions = self.get_mentions()
        self.timestamp = self.message.get('created_at', None)

    def get_sender(self):
        return self.message.get('sender_id', None)

    def get_mentions(self):
        return self.message.get('attachments', [{}])[0].get('user_ids', [])

    def generate_message(self):
        raise NotImplementedError("Implement me!")

    def generate_data(self):
        raise NotImplementedError("Implement me!")
