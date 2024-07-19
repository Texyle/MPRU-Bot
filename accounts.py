import json

accounts = {}

def save():
  json_obj = json.dumps(accounts, indent=4)
  f = open('accounts.json', 'w')
  f.write(json_obj)


def load():
  global accounts
  f = open('accounts.json', 'r')
  json_obj = f.read()
  accounts = json.loads(json_obj)

def get_ign_by_id(search_id):
  for ign, id in accounts.items():
    if id == search_id:
        return ign
  
