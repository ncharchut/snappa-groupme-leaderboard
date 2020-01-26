import csv
import subprocess


def upload_to_heroku():
    FILE = "./resources/groupme_ids_to_names.csv"
    with open(FILE, 'r') as groupme_ids:
        reader = csv.reader(groupme_ids)
        res = ':'.join(list(map(lambda x: '-'.join(x), reader)))
        print(res)
        # subprocess.call(["heroku", "config:set", f"IDS={res}"])


if __name__ == "__main__":
    upload_to_heroku()
