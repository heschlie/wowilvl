import multiprocessing as mp
import operator
import configparser
import requests

config = configparser.ConfigParser()
config.read("wowapi.cfg")
client_id = config['DEFAULT']['clientID']

# Change these to find your guild
server = "the forgotten coast"
guild = "auxilium"

# Setup threadsafe queue to add jobs to
queue = mp.Queue()

# Battlenet stuff for HTTP GET url/header building
api_uri = 'https://us.api.battle.net'

key = {'apikey': client_id}
member_payload = {'fields': 'members'}
char_items = {'fields': 'items'}


def main():

    # Build the dict to use for the params in the HTTP GET
    payload = key.copy()
    payload.update(member_payload)

    # HTTP GET request with the server and guild from above, and then parse that as json
    r = requests.get(api_uri + '/wow/guild/' + server + '/' + guild, params=payload)
    data = r.json()

    # Grab the members json object which contains all of the characters from
    # the guild, and add them to the queue to be processed
    entries = data['members']
    for char in entries:
        queue.put([char['character']['name'], char['character']])

    # Get the size of the queue for tracking progress, create a threadsafe dict
    # and create a list of jobs/processes to execute on the queue
    total = queue.qsize()
    char_ilvl = mp.Manager().dict()
    jobs = []
    for i in range(20):
        p = mp.Process(target=worker, args=(queue, char_ilvl,))
        jobs.append(p)
        p.start()

    # There may be a much better way to do this, we are simply waiting for the
    # processes to complete and then move on to sorting and printing the
    # characters
    waiting = True
    while waiting:
        i = 0
        for job in jobs:
            if job.is_alive():
                i += 1
        if i == 0:
            waiting = False
        current = (queue.qsize() - total) * -1
        print('\r[{0}/{1}] ({2})'.format(current, total, i), end="", flush=True)

    sorted_ilvl = sorted(char_ilvl.items(), key=operator.itemgetter(1))
    print()
    for k, v in sorted_ilvl:
        print(k, v)


def worker(q, d):
    """Used as a worker thread to process the data pulled from battlenet"""

    while not q.empty():
        # Build the headers to get the correct json that contains average ilvl
        # then grab the next job from the queue for character name and realm
        # to add to the uri
        payload = key.copy()
        payload.update(char_items)
        name, data = q.get()

        # Checking for realm as sometimes this seems to not be there, possibly
        # due to battlenet updates being behind after char moves?  Same with
        # the items object nested if
        if 'realm' in data:
            iData = requests.get(api_uri + '/wow/character/' + data['realm'] + '/' + name, params=payload)
            ilvl = iData.json()
            if 'items' in ilvl:
                d[name] = ilvl['items']['averageItemLevel']


if __name__ == "__main__":
    if client_id == "yourKey":
        print("Please replace the clientID in the wowapi.cfg with your api key")
    else:
        main()