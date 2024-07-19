import math
from urllib import parse, request
import json
from random import randrange
import requests

def search_gif(query):
	api_key='AIzaSyB248wS4MuXgdW4UG9IErAkh86T2pE-B08'
	client_key = 'mpru_bot'

	r = requests.get(
    "https://tenor.googleapis.com/v2/search?q=%s&key=%s&client_key=%s&limit=%s&random=true" % (query, api_key, client_key,  1))
	
	if r.status_code == 200:
		gifs = json.loads(r.content)
		return gifs['results'][0]['media_formats']['gif']['url']
	else:
		return None

def get_server_status(ip: str):
  r = requests.get(f"https://api.mcstatus.io/v2/status/java/{ip}")
  
  if r.status_code == 200:
    return json.loads(r.content)  
  return None

def index_to_column(index):
  letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
  if index >= 26:
    letterA = index_to_column(int(math.floor((index - 1) / 26)))
    letterB = index_to_column(index % 26)
    return letterA + letterB
  else:
    return str(letters[index])
