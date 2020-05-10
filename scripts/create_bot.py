import os
import requests


def create_new_group():
    name = input("Group name: ")
    sharable_link = input("Sharable link? (y/n): ").lower()
    share = sharable_link == 'y'

    token = os.environ.get("ACCESS_TOKEN")
    url = f"https://api.groupme.com/v3/groups"
    params = {'name': name,
              'share': share,
              'token': token}

    msg_rqst = requests.post(url, params=params)
    group = msg_rqst.json()['response']

    return group


def post_bot_message(bot_id, text):
    token = os.environ.get("ACCESS_TOKEN")
    url = "https://api.groupme.com/v3/bots/post"
    params = {'text': text,
              'bot_id': bot_id,
              'token': token}
    requests.post(url, params=params)
    return 200


def create_new_bot(group_id):
    name = input("Bot name: ")

    token = os.environ.get("ACCESS_TOKEN")
    callback_url = os.environ.get("CALLBACK_URL")
    url = "https://api.groupme.com/v3/bots"
    data = {'bot': {'name': name,
                    'group_id': group_id,
                    'callback_url': callback_url}}
    params = {'token': token}

    msg_rqst = requests.post(url, json=data, params=params)
    bot_id = msg_rqst.json()['response']['bot']['bot_id']

    return bot_id


def get_groupme_groups():
    token = os.environ.get("ACCESS_TOKEN")
    url = f"https://api.groupme.com/v3/groups"
    params = {'token': token}

    msg_rqst = requests.get(url, params=params)
    groups = list()
    for group in msg_rqst.json()['response']:
        groups.append({'name': group['name'],
                       'group_id': group['group_id'],
                       'members': list(map(lambda x: {'name': x['name'],
                                                      'user_id': x['user_id']},
                                           group['members']))})

    return groups


def configure_bot(group):
    create_bot = input("Create bot? (y/n): ").lower()
    bot_id = None
    if create_bot != 'y':
        bot_id = input("Not creating bot. Enter bot_id: ")
    else:
        bot_id = create_new_bot(group['group_id'])
    return bot_id


def configure_group():
    create_group = input("Create group? (y/n): ").lower()
    group = None
    if create_group != 'y':
        groups = get_groupme_groups()
        for index, group in enumerate(groups):
            print(f"\t ({index + 1}): {group['name']}")
        group_choice_idx = int(input(f"\nChoose your group "
                                     f"(1-{len(groups)}): ")) - 1
        group = groups[group_choice_idx]
    else:
        group = create_new_group()
    return group


def main():
    # access_token = input("Access token: ")
    # if access_token != '':
    #     os.environ["ACCESS_TOKEN"] = access_token

    # TODO: config script for access token, and callback url.

    group = configure_group()
    bot_id = configure_bot(group)

    post_bot_message(bot_id, "it works!")


if __name__ == "__main__":
    main()
