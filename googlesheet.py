import gspread
from oauth2client.service_account import ServiceAccountCredentials
import myutils
import warnings
import traceback
import numpy

creds = None
sheet = None
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

SPREADSHEET_ID = '1g2xw3UE57fJgZ7c_yXlvY3y0Cj02ZZaREY-oGoVTyMg'

rankup_wks = None
segmented_wks = None
data_wks = None
test_wks = None

player_list = []
rankup_tiers = []
rankup_numbers = []
segmented_tiers = []
segmented_numbers = []
map_list = []
collections = []
rankup_sheet = None
segmented_sheet = None
player_numbers = [[],[]]

warnings.filterwarnings("ignore")

def get_data():
  global player_list, rankup_sheet, segmented_sheet, rankup_tiers, segmented_tiers, collections, rankup_numbers, segmented_numbers, map_list, rankup_wks, segmented_wks, data_wks, player_numbers
  
  try:
    rankup_wks = sheet.worksheet('Ранкапы')
    segmented_wks = sheet.worksheet('Сегментед')
    data_wks = sheet.worksheet('Data')
    
    rankup_sheet = rankup_wks.get_all_values()
    segmented_sheet = segmented_wks.get_all_values()
    player_list = [[], []]
    player_list[0] = rankup_wks.get('rankup_players')[0]
    player_list[1] = rankup_wks.get('segmented_players')[0]

    rankup_tiers, segmented_tiers, collections, rankup_numbers, segmented_numbers = data_wks.batch_get(['rankup_tiers', 'segmented_tiers', 'collections', 'rankup_numbers', 'segmented_numbers'])

    map_list = []
    for tier in rankup_tiers:
      for i in range(1, len(tier)):
        map_list.append(tier[i])
    for tier in segmented_tiers:
      for i in range(1, len(tier)):
        map_list.append(tier[i])

    player_numbers = [[],[]]
    for i in range(len(rankup_sheet)):
      if 'Кол-во пройденных' in rankup_sheet[i][0]:
        player_numbers[0].append(rankup_sheet[i])
    for i in range(len(segmented_sheet)):
      if 'Кол-во пройденных' in segmented_sheet[i][0]:
        player_numbers[1].append(segmented_sheet[i])

  except Exception as e:
    traceback.print_exc()    

def get_completed_in_tier(player, map):
  indexes = get_player_map_indexes(player, map)
  if -1 in indexes:
    return -1

  row_ind = get_tier_completions_row(indexes)
  
  if indexes[0] == 0:
    return int(rankup_sheet[row_ind][indexes[2]])
  else:
    return int(segmented_sheet[row_ind][indexes[2]])

def get_tier_color(tier):
  if tier == 'БРОНЗА':
    color = 0xdd7e6b
  elif tier == "СЕРЕБРО":
    color = 0x999999
  elif tier == "ЗОЛОТО":
    color = 0xf1c232
  elif tier == "ИЗУМРУД":
    color = 0x6aa84f
  elif tier == "РУБИН":
    color = 0xcc0000
  elif tier == "АЛМАЗ":
    color = 0x3c78d8
  elif tier == "ЛЕГЕНДА 1":
    color = 0x274e13
  elif tier == "ЛЕГЕНДА 2":
    color = 0x20124d
  elif tier == "ЛЕГЕНДА 3":
    color = 0x000000
  else:
    color = 0xffffff

  return color

def get_tier_name(map):  
  for tier in rankup_tiers:
    if map in tier:
      res = ['', '']
      res[0] = 'РАНКАП'
      res[1] = tier[0]
      return res
  for tier in segmented_tiers:
    if map in tier:
      res = ['', '']
      res[0] = 'СЕГМЕНТЕД'
      res[1] = tier[0]
      return res

def get_tier_numbers(map):
  for tier in rankup_tiers:
    if map in tier:
      return(rankup_numbers[rankup_tiers.index(tier)])

  for tier in segmented_tiers:
    if map in tier:
      return(segmented_numbers[segmented_tiers.index(tier)])

  return None

def is_completed(player, map):
  indexes = get_player_map_indexes(player, map)

  if indexes[0] == 0:
    return rankup_sheet[indexes[1]][indexes[2]] == '✔'
  if indexes[0] == 1:
    return segmented_sheet[indexes[1]][indexes[2]] == '✔'

  return False

def get_collection(map):
  collection = [map]
  for col in collections:
    if map in col:
      collection = col[:col.index(map)+1]

  return collection

def get_tier_completions_row(indexes):
  current_sheet = None
  if indexes[0] == 0:
    current_sheet = rankup_sheet
  else:
    current_sheet = segmented_sheet

  for i in range(indexes[1], len(current_sheet)):
    if len(str(current_sheet[i][indexes[2]])) > 0:
      if str.isnumeric(str(current_sheet[i][indexes[2]])):
        return i

def get_player_map_indexes(player, map):
  indexes = [-1, -1, -1]
  
  found = False
  for i in range(len(rankup_sheet)):
    if rankup_sheet[i][0] == map:
      found = True
      indexes[0] = 0
      indexes[1] = i
      break
      
  if not found:
    for i in range(len(segmented_sheet)):
      if segmented_sheet[i][0] == map:
        found = True
        indexes[0] = 1
        indexes[1] = i
        break

  for i in range(len(player_list[indexes[0]])):
    if player_list[indexes[0]][i] == player:
      indexes[2] = i+1
      break

  return indexes

def check_maps(player, maps):
  try:
    body_rankup = []
    body_segmented = []
    value = [['✔']]

    for i in range(len(maps)):
      indexes = get_player_map_indexes(player, maps[i])
  
      if (-1 in indexes):
        return -1
  
      if indexes[0] == 0:
        if rankup_sheet[indexes[1]][indexes[2]] != '✔':
          rankup_sheet[indexes[1]][indexes[2]] = '✔'
          
          row_ind = get_tier_completions_row(indexes)
          rankup_sheet[row_ind][indexes[2]] = int(rankup_sheet[row_ind][indexes[2]])+1
        
        body_rankup.append({'range': f'{myutils.index_to_column(indexes[2])}{indexes[1]+1}', 'values': value})        

      elif indexes[0] == 1:
        if segmented_sheet[indexes[1]][indexes[2]] != '✔':
          segmented_sheet[indexes[1]][indexes[2]] = '✔'
          
          row_ind = get_tier_completions_row(indexes)
          segmented_sheet[row_ind][indexes[2]] = int(segmented_sheet[row_ind][indexes[2]])+1

        body_segmented.append({'range': f'{myutils.index_to_column(indexes[2])}{indexes[1]+1}', 'values': value})        

    if len(body_rankup) > 0: rankup_wks.batch_update(body_rankup)
    if len(body_segmented) > 0: segmented_wks.batch_update(body_segmented)
      
    return 0
  except Exception as e:
    traceback.print_exc()
    return 1

def init():
  global sheet
  
  scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive.file',
         'https://www.googleapis.com/auth/drive']
  credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json'
            , scope)
  gc = gspread.authorize(credentials)
  sheet = gc.open('MPRU Skill Rating')

  get_data()

  
