import discord
import typing
from discord import app_commands, utils, ui
from discord.ext import commands
import requests
from gspread_formatting import *
from oauth2client.service_account import ServiceAccountCredentials
import json
import traceback
import os
import random
from datetime import datetime
from functools import cmp_to_key
from emojis import Emojis

class Sheet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ids = {
            'spreadsheet': '1OINu_HpOpjaGGyEWIeR_sCducvlq-FguIN4JTpzDifw',
            'rankup': 0,
            'segmented': 1302560255
        }
        self.credentials = None
        self.open_spreadsheet()

        self.maps_data = None
        self.players_data = None
        self.collections_data = None
        self.hidden_maps = []
        self.load_data()
        self.load_data()
        self.map_list = self.get_map_list()
        
        self.mpru_guild = self.bot.get_guild(1041059132448444509)
        self.announce_channel = self.mpru_guild.get_channel(1136596727546253322)
        self.ping_role_id = 1139465950249361418
                    
            
    group = app_commands.Group(name='map', description="Команды для взаимодействия с таблицей карт")
    
    async def check_maps(self, maps_string: str, ign: str = None, user: discord.Member = None, dont_announce: bool = False):
        '''
        Error codes:
        -1: Player not found
        -2: Map not found, returns map name
        '''
        # Check if player exists
        player = None
        
        if ign == None:
            player = self.find_player_by_user(user)
        else:
            player = self.find_player_by_ign(ign)
            
        if player == None:
            return -1, []
        
        # Validate map list
        maps = maps_string.split(', ')
        validated_maps = []
        for map in maps:
            if map in self.map_list:
                validated_maps.append(map)
            else:
                found = False
                for m in self.map_list:
                    if map == m.lower():
                        validated_maps.append(m)
                        found = True
                        break
                if not found:
                    return -2, [map]
        maps = validated_maps
        
        # Add collections
        maps_with_collections = []
        for map in maps:
            for collection in self.collections_data:
                if map in collection['maps']:
                    collection_slice = slice(0, collection['maps'].index(map))
                    maps_with_collections.extend(collection['maps'][collection_slice])
                    break
            maps_with_collections.append(map)
        maps = maps_with_collections
        
        # Check maps
        checked_maps = []
        for map in maps:     
            # Check map       
            type = self.get_map_type(map)
                
            tier = None
            for t in self.maps_data[type]:
                if map in t['maps']:
                    tier = t
            if player['ign'] not in tier['maps'][map]['victors']:
                date = datetime.today()
                date = datetime.strftime(date, '%d.%m.%Y')
                tier['maps'][map]['victors'][player['ign']] = {'date': date}
                checked_maps.append(map)
                
                # Announce map
                if tier['announce_maps'] and not dont_announce:
                    ping = 0
                    if tier['ping_maps']:
                        if tier['ping_everyone']: 
                            ping = 2
                        else:
                            ping = 1
                    await self.announce_map(player['discord_id'], map, ping)
        
        # Check and announce tier completion
        for map in checked_maps:
            tier = self.get_map_tier(map)
            player_tier_count = self.count_player_maps_in_tier(player['ign'], tier)
            if player_tier_count == tier['qualify_amount'] or player_tier_count == len(tier['maps']):
                ping = 0
                if tier['ping_tier']:
                    if tier['ping_everyone']: 
                        ping = 2
                    else:
                        ping = 1
                        
                full = False
                if player_tier_count == len(tier['maps']):
                    full = True
                
                type_ru = ''
                if type == 'rankups':
                    type_ru = 'РАНКАП'
                elif type == 'segmented':
                    type_ru = 'СЕГМЕНТЕД'
                
                if tier['announce_tier'] and not dont_announce:
                    await self.announce_tier(full, player['discord_id'], tier, ping, type_ru)
            
        self.sync_players_data()
        self.save_data()
        await self.update_roles(ign=player['ign'])
        
        return 0, checked_maps
    
    def uncheck_map(self, map: str, ign: str = None, user: discord.Member = None):
        '''
        Error codes:
        -1: Player not found
        -2: Map not found
        -3: Tier error
        '''
        # Check if player exists
        player = None
        
        if ign == None:
            player = self.find_player_by_user(user)
        else:
            player = self.find_player_by_ign(ign)
            
        if player == None:
            return -1
        
        # Validate map
        if map not in self.map_list:
            found = False
            for m in self.map_list:
                if map.lower() == m.lower():
                    map = m
                    found = True
                    break
            if not found:
                return -2
           
        # Uncheck map 
        type = self.get_map_type(map)
            
        #   Uncheck map in maps_data
        tier = None
        for t in self.maps_data[type]:
            if map in t['maps']:
                tier = t
        if tier == None:
            return -3
        if player['ign'] in tier['maps'][map]['victors']:
            tier['maps'][map]['victors'].pop(player['ign'])
            
        self.sync_players_data()
        self.save_data()
            
        return 0
    
    async def announce_map(self, user_id, map: str, ping: int):
        if self.announce_channel == None:
            return
        
        screenshot_name = map.lower().replace(' ', '')
        screenshot_path = f'screenshots/{screenshot_name}.jpg'
        img_url = f'attachment://{screenshot_name}.jpg'
        screenshot = utils.MISSING
        if os.path.isfile(screenshot_path):
            screenshot = discord.File(screenshot_path)
        
        ping_msg = ''
        if ping == 1:
            role = utils.get(self.mpru_guild.roles, id=self.ping_role_id)
            ping_msg = f'{role.mention}'
        elif ping == 2:
            ping_msg = '@everyone'
        
        msg = f"Поздравляем игрока <@{user_id}> с прохождением карты **{map}**!"
        tier = self.get_map_tier(map)
        if tier == None:
            return
        tier_color = tier['colors']['main']
        color = discord.Color.from_rgb(int(tier_color['red']*255), int(tier_color['green']*255), int(tier_color['blue']*255))
        gg_emoji = str(discord.utils.get(self.bot.emojis, name='gg'))
        embed = discord.Embed(title=f'{gg_emoji}{gg_emoji}{gg_emoji}',
                              description=msg,
                              color=color)
        embed.set_image(url=img_url)

        await self.announce_channel.send(content=ping_msg, embed=embed, file=screenshot)
    
    async def announce_tier(self, full: bool, user_id, tier: dict, ping: int, type: str):
        if self.announce_channel == None:
            return
        
        ping_msg = ''
        if ping == 1:
            role = utils.get(self.mpru_guild.roles, id=self.ping_role_id)
            ping_msg = f'{role.mention}'
        elif ping == 2:
            ping_msg = '@everyone'
        
        msg = ''
        if full:
            msg = f"Поздравляем игрока <@{user_id}> с прохождением ВСЕХ КАРТ тира **{tier['tier_name']}** в режиме **{type}**!"
        else:
            msg = f"Поздравляем игрока <@{user_id}> с прохождением тира **{tier['tier_name']}** в режиме **{type}**!"
        
        tier_color = tier['colors']['main']
        color = discord.Color.from_rgb(int(tier_color['red']*255), int(tier_color['green']*255), int(tier_color['blue']*255))
        gg_emoji = str(discord.utils.get(self.bot.emojis, name='gg'))

        embed = discord.Embed(title=f'{gg_emoji}{gg_emoji}{gg_emoji}',
                              description=msg,
                              color=color)

        await self.announce_channel.send(content=ping_msg, embed=embed)

    def upload_to_spreadsheet(self):        
        try:            
            def build_rows(type: str):       
                players_data = self.get_sorted_players_in_type(type) 
                maps_data = self.maps_data[type]
                                        
                values = []
                
                def cell(value='', bold=False, color={'red': 1, 'green': 1, 'blue': 1, 'alpha': 1}, text_color={'red': 0, 'green': 0, 'blue': 0, 'alpha': 1}, font_size=10, horizontal_alignment="CENTER", vertical_alignment='MIDDLE', wrap_strategy='OVERFLOW_CELL', note=''):
                    return {
                        'value': value, 
                        'bold': bold, 
                        'color': color, 
                        'fontSize': font_size, 
                        'horizontalAlignment': horizontal_alignment,
                        'verticalAlignment': vertical_alignment,
                        'wrapStrategy': wrap_strategy,
                        'foregroundColor': text_color,
                        'note': note
                    }
                                
                # First row
                values.append([cell('Роль выдаётся за прохождение указанного количества карт, и при условии прохождения всех предыдущих тиров.', horizontal_alignment='LEFT', wrap_strategy='WRAP')])
                
                # Players
                ign_row = [cell()]
                map_count_row = [cell('Пройдено карт', bold=True)]
                for player in players_data:
                    ign_row.append(cell(player['ign']))
                    map_count = 0
                    for m in player['maps'][type]:
                        if m not in self.hidden_maps:
                            map_count += 1
                    map_count_row.append(cell(str(map_count), bold=True))
                values.append(ign_row)
                values.append([cell()])
                values.append(map_count_row)
                
                # Tiers
                for tier in maps_data:
                    tier_row = [cell(f'{tier["tier_name"]}\nПройти любые {tier["qualify_amount"]}', bold=True, color=tier['colors']['main'], font_size=12, text_color=tier['colors']['text'])]
                    for i in range(len(players_data)+14):
                        tier_row.append(cell('', color=tier['colors']['main']))
                    values.append(tier_row)
                    tier_count = 0
                    for map, map_data in tier['maps'].items():
                        if map in self.hidden_maps:
                            continue
                        tier_count += 1
                        difficulty = 'N/A'
                        quality = 'N/A'
                        reviews = map_data.get('reviews')
                        if reviews and len(reviews) > 0:
                            dif_sum = 0.0
                            qual_sum = 0.0
                            dif_count = 0.0
                            qual_count = 0.0
                            for review in reviews:
                                dif_sum += float(review['difficulty'])
                                qual_sum += float(review['quality'])
                                dif_count += 1
                                qual_count += 1
                            difficulty = str(round(dif_sum/dif_count, 1))
                            quality = str(round(qual_sum/qual_count, 1))
                        info = map_data.get('info')
                        server_ip = 'Неизвестно'
                        is_on_pkc = 'Неизвество'
                        if info:
                            server_ip = info['server']['ip']
                            is_on_pkc = 'Да' if info['is_on_pkc'] else 'Нет'
                        note = f'Сервер: {server_ip}\n\nСложность в рамках тира: {difficulty}\nКачество: {quality}\n\nЕсть на ПКЦ: {is_on_pkc}'
                        map_row = [cell(map, color=tier['colors']['secondary'], text_color=tier['colors']['text'], note=note)]
                        for player in players_data:
                            if player['ign'] in map_data['victors']:
                                map_row.append(cell('✔'))
                            else:
                                map_row.append(cell())
                        values.append(map_row)
                    completed_row = [cell(f'Кол-во пройденных (из {tier_count})', True, color=tier['colors']['secondary'], font_size=12, text_color=tier['colors']['text'])]
                    for player in players_data:
                        map_count = self.count_player_maps_in_tier(player['ign'], tier)
                        color = None
                        text_color = None
                        if map_count == tier_count:
                            color = tier['colors']['main']
                            text_color = tier['colors']['text']
                        elif map_count >= tier['qualify_amount']:
                            color = tier['colors']['secondary']
                            text_color = tier['colors']['text']
                        else:
                            color = {'red': 1, 'green': 1, 'blue': 1, 'alpha': 1}
                            text_color = {'red': 0, 'green': 0, 'blue': 0, 'alpha': 1}
                        completed_row.append(cell(str(map_count), bold=True, color=color, text_color=text_color))
                    values.append(completed_row)
                                
                # Format for request                
                rows = [{"values": [{"userEnteredValue": {"stringValue": v['value']},
                                     "userEnteredFormat": {
                                         "textFormat": {"bold": v['bold'], "fontSize": v['fontSize'], "foregroundColorStyle": {"rgbColor": v['foregroundColor']}}, 
                                         "backgroundColor": v['color'],
                                         "horizontalAlignment": v['horizontalAlignment'],
                                         "verticalAlignment": v['verticalAlignment'],
                                         "wrapStrategy": v['wrapStrategy']},
                                     "note": v['note']} 
                                    for v in row]} for row in values]
                
                return rows
            
            rankup_rows = build_rows('rankups')
            segmented_rows = build_rows('segmented')
            
            def clear_request(id):
                return {
                    "updateCells": {
                        "rows": [],
                        "fields": "*",
                        "range": {
                            "sheetId": id,
                            "startRowIndex": 0,
                            "startColumnIndex": 0
                        }
                    }
                }
                
            def update_cells_request(id, rows):
                return {
                    "updateCells": {
                        "rows": rows,
                        "fields": "*",
                        "start": {
                            "sheetId": id,
                            "rowIndex": 0,
                            "columnIndex": 0
                        }
                    }
                }
            
            def auto_resize_dimensions_request(id, dimension):
                return {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": id,
                            "dimension": dimension,
                            "startIndex": 0
                        }
                    }
                }
            
            def merge_cells_request(id):
                return ({"mergeCells": {
                        "range": {
                            "sheetId": id,
                            "startRowIndex": 0,
                            "endRowIndex": 3,
                            "startColumnIndex": 0,
                            "endColumnIndex": 1
                        },
                        "mergeType": "MERGE_ALL"
                    }},
                    {"mergeCells": {
                        "range": {
                            "sheetId": id,
                            "startRowIndex": 1,
                            "endRowIndex": 3,
                            "startColumnIndex": 1
                        },
                        "mergeType": "MERGE_COLUMNS"
                    }
                })
            
            def update_sheet_properties_request(id, type):
                rows = 4
                for tier in self.maps_data[type]:
                    rows += len(tier['maps'])+2
                columns = len(self.players_data)+15
                
                return {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": id,
                            "gridProperties": {
                                "rowCount": rows,
                                "columnCount": columns
                            }
                        },
                        "fields": "gridProperties.rowCount,gridProperties.columnCount"
                    }
                }
            
            rankup_id = self.ids['rankup']
            segmented_id = self.ids['segmented']
                        
            reqs = [
                clear_request(rankup_id),
                clear_request(segmented_id),
                update_sheet_properties_request(rankup_id, 'rankups'),
                update_sheet_properties_request(segmented_id, 'segmented'),
                *merge_cells_request(rankup_id),
                *merge_cells_request(segmented_id),
                update_cells_request(rankup_id, rankup_rows),
                update_cells_request(segmented_id, segmented_rows),
                auto_resize_dimensions_request(rankup_id, 'ROWS'),
                auto_resize_dimensions_request(segmented_id, 'ROWS')
            ]
                        
            body = {
                "requests": reqs,
                "includeSpreadsheetInResponse": False,
                "responseRanges": [],
                "responseIncludeGridData": False
            }
            
            def set_default(obj):
                if isinstance(obj, set):
                    return list(obj)
                raise TypeError
                                    
            res = requests.post('https://sheets.googleapis.com/v4/spreadsheets/' + self.ids['spreadsheet'] + ':batchUpdate',
                                headers={"Authorization": "Bearer " + self.credentials.get_access_token().access_token, "Content-Type": "application/json"},
                                data=json.dumps(body, default=set_default))  
            
            print(f"API response: {res.json()}")
                                
            return 0
        except Exception as e:
            traceback.print_exc()
            return e
    
    async def update_roles(self, user: discord.Member = None, ign: str = None):
        player = None
        
        if ign == None:
            player = self.find_player_by_user(user)
        else:
            player = self.find_player_by_ign(ign)
            
        if player == None:
            return -1
        
        if not user:
            user = self.mpru_guild.get_member(player['discord_id'])
        
        role_ids = []
        highest_tier = {'rankups': [1136220288628039781, True], 'segmented': [1136221256925053019, True]}
        for typename, type in self.maps_data.items():
            for tier in type:
                completed = self.count_player_maps_in_tier(player['ign'], tier)
                if highest_tier[typename][1]:
                    if completed >= tier['qualify_amount']:
                        highest_tier[typename][0] = tier['roles']['regular']
                    else:
                        highest_tier[typename][1] = False
                if completed == self.count_maps_in_tier(tier):
                    role_ids.append(tier['roles']['plus'])
        role_ids.append(highest_tier['rankups'][0])
        role_ids.append(highest_tier['segmented'][0])
        
        role_ids_to_remove = [
            1136220288628039781,
            1147989284939366552,
            1136220555301896242,
            1147990133002477708,
            1136220665188450387,
            1147990622041546862,
            1136220732918083595,
            1147990779034337491,
            1136220790245834832,
            1148121483319709706,
            1207314628414144562,
            1207315271908462652,
            1136220851876937828,
            1147991870010564701,
            1136220898760859708,
            1147991897244176467,
            1136221035981709416,
            1147991944065187962,
            1136221117405724702,
            1147991978034868396,
            1136221256925053019,
            1148120754840412222,
            1136221341821968405,
            1148120975334969394,
            1136221344309194822,
            1148121183229853776,
            1136221346641236031,
            1148121348112142416,
            1136221711193362503,
            1148121483319709706,
            1136221348230873148,
            1148121673577541722,
            1136221349577228368,
            1148121885415067780,
            1136221351347240980,
            1148122322092429333,
            1136221353708617738,
            1148122366388482121
        ]
        
        roles_to_remove = []
        for role in user.roles:
            if role.id in role_ids_to_remove:
                if not role.id in role_ids: 
                    roles_to_remove.append(role)
                else:
                    role_ids.remove(role.id)
        await user.remove_roles(*roles_to_remove)
        
        roles = []
        for role_id in role_ids:
            roles.append(utils.get(self.mpru_guild.roles, id=role_id))
        
        await user.add_roles(*roles)
        
    @group.command(name="check", description="Отметить карту игроку. Можно указать либо его дискорд тег, либо игровой ник.")
    async def map_check_command(self, interaction: discord.Interaction, user: discord.Member=None, ign: str = None, maps: str = None, dont_announce: bool = False):        
        allowed = False
        for role in interaction.user.roles:
            if role.name == "Админ" or role.name == "Хелпер":
                allowed = True    
        
        if not allowed:
            await interaction.response.send_message(f'А тебе низя :/', ephemeral=True)
            return   
        
        if user == None and ign == None:
            await interaction.response.send_message(f'Необходимо указать либо пользователя в дискорде, либо его ник.', ephemeral=True)
            return
        elif maps == None:
            await interaction.response.send_message(f'А что отмечать то? ¯\_(ツ)_/¯', ephemeral=True)
            return
        
        await interaction.response.defer()
        
        err, checked_maps = await self.check_maps(maps, ign=ign, user=user, dont_announce=dont_announce)
        if err == 0:
            if ign == None:
                ign = self.find_player_by_user(user)['ign']
            if len(checked_maps) > 0:
                embed = discord.Embed(title='Карты отмечены', color=discord.Color.green())
                description = f'Игрок: {ign}\n\nКарты:'
                for map in checked_maps:
                    description += f'\n* {map}'
                embed.description = description
                await interaction.followup.send(embed=embed)
                self.upload_to_spreadsheet()
                return
            else:
                await interaction.followup.send('У игрока уже отмечены все указанные карты')
                return
        elif err == -1:
            await interaction.followup.send('Указанный игрок не найден. Зарегистрировать нового игрока можно командой ``/map addplayer``')
            return
        elif err == -2:
            await interaction.followup.send(f'Ошибка: не найдена карта {checked_maps[0]}')
            return
    
    @group.command(name='uncheck', description='Убрать у игрока карту из списка отмеченных')
    async def map_uncheck_command(self, interaction: discord.Interaction, user: discord.Member=None, ign: str = None, map: str = None):
        allowed = False
        for role in interaction.user.roles:
            if role.name == "Админ" or role.name == "Хелпер":
                allowed = True    
        
        if not allowed:
            await interaction.response.send_message(f'А тебе низя :/', ephemeral=True)
            return   
        
        if user == None and ign == None:
            await interaction.response.send_message(f'Необходимо указать либо пользователя в дискорде, либо его ник.', ephemeral=True)
            return
        elif map == None:
            await interaction.response.send_message(f'А что отмечать то? ¯\_(ツ)_/¯', ephemeral=True)
            return
        
        err = self.uncheck_map(map=map, ign=ign, user=user)
        if err == 0:
            if ign == None:
                ign = self.find_player_by_user(user)['ign']
            await interaction.response.send_message(f"Успешно удалена карта {map} у игрока {ign}", ephemeral=True)
            self.upload_to_spreadsheet()
            return
        elif err == -1:
            await interaction.response.send_message('Указанный игрок не найден. Зарегистрировать нового игрока можно командой ``/map addplayer``', ephemeral=True)
            return
        elif err == -2:
            await interaction.response.send_message(f'Ошибка: не найдена карта {map}')
            return
        elif err == -3:
            await interaction.response.send_message(f'Ошибка при поиске ')
            return
    
    @group.command(name='info', description='Просмотр информации о карте')
    async def map_info_command(self, interaction: discord.Interaction, map: str):
        if map not in self.map_list:
            found = False
            for m in self.map_list:
                if m.lower() == map.lower():
                    map = m
                    found = True
            if not found:
                await interaction.response.send_message(f'Карта с названием "{map}" не найдена', ephemeral=True)
                return
        
        await interaction.response.defer()
        
        embeds = self.build_map_info_embeds(map)
        screenshot = self.get_screenshot(map)
        await interaction.followup.send(embed=embeds[0], view=Views.MapInfoView(embeds, map), ephemeral=False, file=screenshot or utils.MISSING)
    
    @group.command(name='updateroles', description='Обновить скилл-рейтинг роли у игрока')
    async def update_roles_command(self, interaction: discord.Interaction, user: discord.Member):
        allowed = False
        for role in interaction.user.roles:
            if role.name == "Админ" or role.name == "Хелпер":
                allowed = True    
        
        if not allowed:
            await interaction.response.send_message(f'А тебе низя :/', ephemeral=True)
            return
        
        await interaction.response.send_message('Роли игрока обновлены')
        
        await self.update_roles(user=user)
    
    @group.command(name='noscreenshot')
    async def no_screenshot_command(self, interaction: discord.Interaction):
        msg = 'Список карт без скриншота:'
        for map in self.map_list:
            filename = map.lower().replace(' ', '') + '.jpg'
            if not os.path.isfile('screenshots/'+filename):
                msg += f'\n{map}'
        
        embed = discord.Embed(title='Карты без скриншота', description=msg)
        await interaction.response.send_message(embed=embed)
    
    @group.command(name='s')
    async def add_screenshot_command(self, interaction: discord.Interaction, map: str, screenshot: discord.Attachment):
        if interaction.user.id not in [540505831116898305, 269105396587823104, 513011868063760384]:
            await interaction.response.send_message('не-а', ephemeral=True)

        file_name = map.lower().replace(' ', '')
        file = await screenshot.to_file()
        
        await screenshot.save(f'screenshots/{file_name}.jpg')
        await interaction.response.send_message(f'Скриншот для карты **{map}** сохранён', file=file)
    
    @group.command(name='review', description='Добавить отзыв по карте')
    async def review_command(self, interaction: discord.Interaction, map: str):
        if map not in self.map_list:
            found = False
            for m in self.map_list:
                if m.lower() == map.lower():
                    map = m
                    found = True
            if not found:
                await interaction.response.send_message(f'Карта с названием "{map}" не найдена', ephemeral=True)
                return
        
        player = self.find_player_by_user(interaction.user)
        found = False
        for m in player['maps']['rankups']:
            if m.lower() == map.lower():
                found = True
                break
        if not found: 
            for m in player['maps']['segmented']:
                if m.lower() == map.lower():
                    found = True
                    break
        if not found:
            await interaction.response.send_message(f'Оставить отзыв можно только после прохождения карты', ephemeral=True)
            return
        
        map_obj = self.get_map_tier(map)['maps'][map]
        reviews = map_obj.get('reviews')
        if reviews:
            for review in reviews:
                if review['author'] == interaction.user.id:
                    msg = 'Вы уже оставляли отзыв по этой карте:\n'
                    msg += f'```Сложность: {review["difficulty"]}/10\n'
                    msg += f'Качество: {review["quality"]}/10\n'
                    msg += f'Комментарий: {review["comment"]}```\n'
                    msg += 'Вы уверены что хотите его изменить?'
                    modal = Modals.ReviewModal(self, map, default_difficulty=review['difficulty'], default_quality=review['quality'], default_comment=review['comment'])
                    await interaction.response.send_message(msg, view=Views.ReviewEditConfirmView(modal), ephemeral=True)
                    return
        
        await interaction.response.send_modal(Modals.ReviewModal(self, map))
        self.upload_to_spreadsheet()
    
    @group.command(name='noreview', description='Показывает список пройденных карт у которых ещё не оставлен отзыв')
    async def noreview_command(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        user_ign = self.find_player_by_id(user_id)['ign']
        maps = []
        
        for type_name, type in self.maps_data.items():
            for tier in type:
                for map_name, map in tier['maps'].items():
                    if map_name in self.hidden_maps:
                        continue
                    if user_ign not in map['victors']:
                        continue
                    reviews = map.get('reviews')
                    if not reviews:
                        maps.append(map_name)
                        continue
                    found = False
                    for review in reviews:
                        if review['author'] == user_id:
                            found = True
                    if not found:
                        maps.append(map_name)
        
        msg = ''                
        for map in maps:
            msg += f'-{map}\n'
        
        embed = discord.Embed(title='Список пройденных карт у которых ещё нет отзыва', description=msg)
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
        
    @group.command(name='nodate', description='Выводит список игроков и пройденных ими карт, у которых ещё не установлена дата прохождения')
    async def nodate_command(self, interaction: discord.Interaction, user: discord.Member=None):
        output = self.get_nodates()
        
        player_ = None
        if user:
            player_ = self.find_player_by_user(user)['ign']
            if not player_:
                await interaction.response.send_message(f'Указанный пользователь не найден в системе', ephemeral=True)
                return
        
        msg = ''
        overflow = False
        for player, maps in output.items():
            if player_ and player != player_: continue
            if overflow: break
            msg += f'* {player}\n```'
            for map in maps:
                msg += map+', '
                if len(msg) > 4000:
                    overflow = True
                    msg += '```\nупси дупси больше в сообщение не помещается'
                    break
            msg += '```\n'
                        
        embed = discord.Embed(title='Отсутствующие даты', description=msg, color=discord.Color.pink())
        embed.set_footer(text='Установить дату можно командой /maps setdate')
        
        await interaction.response.send_message(embed=embed)
    
    @group.command(name='setdate', description='Установить дату прохождения карты игроком')
    async def setdate_command(self, interaction: discord.Interaction,  user: discord.Member, map: str, date: str):
        allowed = False
        for role in interaction.user.roles:
            if role.name == "Админ" or role.name == "Хелпер":
                allowed = True    
        
        if not allowed:
            await interaction.response.send_message(f'А тебе низя :/', ephemeral=True)
            return 
        
        player = self.find_player_by_user(user)
        if not player:
            await interaction.response.send_message(f'Указанный пользователь не найден в системе', ephemeral=True)
            return
        
        ign = player['ign']
        
        map_obj = self.get_map(map)
        if not map_obj:
            await interaction.response.send_message(f'Карта с названием "{map}" не найдена', ephemeral=True)
            return
        
        try:
            date_obj = datetime.strptime(date, '%d.%m.%Y')
        except ValueError:
            await interaction.response.send_message(f'Дата должна быть указана в формате "день.месяц.год" (01.01.2001)', ephemeral=True)
            return
        
        date = datetime.strftime(date_obj, '%d.%m.%Y')
        map_obj['victors'][ign]['date'] = date
        self.save_data()
        
        msg = f'Установлена дата ``{date}`` игроку ``{ign}`` на карте ``{map}``'
        embed = discord.Embed(color=discord.Colour.pink(), description=msg)
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    @map_check_command.autocomplete('maps')
    async def map_string_autocompletion(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        map_choices = []
        
        typed_maps = current.split(', ')
        
        before_last = ''
        for i in range(len(typed_maps)-1):
            before_last += typed_maps[i] + ', '
        
        last_map = typed_maps[len(typed_maps)-1]
        for map in self.map_list:
            if last_map.lower() in map.lower():
                map_choices.append(app_commands.Choice(name=before_last+map, value=before_last+map))
                                
        return map_choices[:25]
    
    @map_uncheck_command.autocomplete('map')
    @map_info_command.autocomplete('map')
    @add_screenshot_command.autocomplete('map')
    @review_command.autocomplete('map')
    @setdate_command.autocomplete('map')
    async def map_autocompletion(self, interaction: discord.Integration, current: str) -> typing.List[app_commands.Choice[str]]:
        map_choices = []
        for map in self.map_list:
            if current.lower() in map.lower():
                map_choices.append(app_commands.Choice(name=map, value=map))
                
        return map_choices[:25]
            
    @group.command(name='addmap', description='Добавить новую карту в таблицу')
    @app_commands.choices(type=[
                           discord.app_commands.Choice(name='Ранкап', value='rankups'),
                           discord.app_commands.Choice(name='Сегментед', value='segmented')],
                          tier=[
                            discord.app_commands.Choice(name=t, value=t) for t in ['Бронза', 'Серебро', 'Золото', 'Изумруд', 'Рубин', 'Топаз', 'Алмаз', 'Легенда 1', 'Легенда 2', 'Легенда 3']
                          ])
    async def add_map(self, interaction: discord.Interaction, name: str, type: str, tier: str):
        if interaction.user.id != 269105396587823104:
            await interaction.response.send_message('не-а', ephemeral=True)
            return
        
        found_tier = False
        for t in self.maps_data[type]:
            if t['tier_name'] == tier:
                t['maps'][name] = {'victors': {}}
                found_tier = True
        
        if not found_tier:
            await interaction.response.send_message('Ошибка: не найден тир', ephemeral=True)
            return
                            
        self.save_data()
        
        await interaction.response.send_message(f'Добавлена карта **{name}** ({type} - {tier})', ephemeral=False)
             
    @group.command(name='addplayer', description='Добавить игрока в таблицу')
    async def add_player(self, interaction: discord.Interaction, ign: str, user: discord.Member):
        allowed = False
        for role in interaction.user.roles:
            if role.name == "Админ" or role.name == "Хелпер":
                allowed = True    
        
        if not allowed:
            await interaction.response.send_message(f'А тебе низя :/', ephemeral=True)
            return      
        
        for player in self.players_data:
            if player['ign'] == ign:
                await interaction.response.send_message(f'Этот ник уже зарегестрирован на пользователя <@{player["discord_id"]}>', ephemeral=True)
                return
            if player['discord_id'] == user.id:
                await interaction.response.send_message(f'Пользователь <@{user.id}> уже зарегестрирован в системе под ником {player["ign"]}', ephemeral=True)
                return
            
        self.players_data.append({'ign': ign, 'discord_id': user.id, 'maps': {'rankups': [], 'segmented': []}})
        embed = discord.Embed()
        embed.description = f'Пользователь <@{user.id}> был успешно зарегестрирован в системе под ником {ign}'
        await interaction.response.send_message(embed=embed)
        
        self.save_data()
            
    @group.command(name='reload', description='Загрузить данные таблицы из файла сервера в бота')
    async def reload(self, interaction: discord.Interaction):
        if interaction.user.id != 269105396587823104:
            await interaction.response.send_message('не-а', ephemeral=True)
            return
        
        self.load_data()
        self.map_list = self.get_map_list()
        await interaction.response.send_message('Данные загружены', ephemeral=True)
        
    @group.command(name='upload', description='Копировать данные таблицы из бота в гугл таблицу')
    async def upload_command(self, interaction: discord.Interaction):
        if interaction.user.id != 269105396587823104:
            await interaction.response.send_message('не-а', ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        err = self.upload_to_spreadsheet()
        if err != 0:
            await interaction.followup.send(f'Ошибка записи : {str(err)[:1000]}', ephemeral=True)
        else:
            await interaction.followup.send('Успех', ephemeral=True)
    
    @group.command(name='sync', description='Синхронизировать файл игроков с файлом карт')
    async def sync_command(self, interaction: discord.Interaction):
        if interaction.user.id != 269105396587823104:
            await interaction.response.send_message('не-а', ephemeral=True)
            return
        
        self.sync_players_data()
        await interaction.response.send_message('Файл синхронизирован', ephemeral=True)
    
    @group.command(name='random', description='Случайная карта')
    async def random_map(self, interaction: discord.Interaction, all_maps: bool = False):    
        if not all_maps:
            player = self.find_player_by_user(interaction.user)
            all_maps_list = self.get_map_list();
            map_list = [];
            for map_name in all_maps_list:
                if player['ign'] not in self.get_map(map_name)['victors']:
                    map_list.append(map_name);
        else:
            map_list = self.get_map_list();
        
        response = ''
        if not all_maps:
            response = f'Случайная карта из непройденных: **{random.choice(map_list)}**'
        else:
            response = f'Случайная карта из таблицы: **{random.choice(map_list)}**'		
        await interaction.response.send_message(response);
    
    def sync_players_data(self):
        for player in self.players_data:
            for typename, type in self.maps_data.items():
                player_maps = []
                for tier in type:
                    for mapname, map in tier['maps'].items():
                        if player['ign'] in map['victors']:
                            player_maps.append(mapname)
                player['maps'][typename] = player_maps
        self.save_data()
    
    def get_map_list(self):
        map_list = []
        
        for tier in self.maps_data['rankups']:
            for map in tier['maps']:
                if map not in self.hidden_maps:
                    map_list.append(map)
        for tier in self.maps_data['segmented']:
            for map in tier['maps']:
                if map not in self.hidden_maps:
                    map_list.append(map)
                
        return map_list
    
    def get_map(self, map):
        for typename, type in self.maps_data.items():
            for tier in type:
                for mapname, map_obj in tier['maps'].items():
                    if map.lower() == mapname.lower():
                        return map_obj
        
        return None
    
    def get_map_tier(self, map):
        for typename, type in self.maps_data.items():
            for tier in type:
                for m in tier['maps']:
                    if map.lower() == m.lower():
                        return tier
        
        return None
    
    def get_map_type(self, map):
        for typename, type in self.maps_data.items():
            for tier in type:
                for m in tier['maps']:
                    if map.lower() == m.lower():
                        return typename
                
        return ''
    
    def get_nodates(self):
        output = {}
        for typename, type in self.maps_data.items():
            for tier in type:
                for mapname, map in tier['maps'].items():
                    if mapname in self.hidden_maps:
                        continue
                    for victor, data in map['victors'].items():
                        if data['date'] == '':
                            if output.get(victor):
                                output[victor].append(mapname)
                            else:
                                output[victor] = [mapname]
        
        return output
    
    def count_player_maps_in_tier(self, ign: str, tier: dict):
        count = 0
        for mapname, map in tier['maps'].items():
            if mapname not in self.hidden_maps:
                if ign in map['victors']:
                    count += 1     
        return count
    
    def count_maps_in_tier(self, tier: dict):
        count = 0
        for mapname, map in tier['maps'].items():
            if mapname not in self.hidden_maps:
                count += 1
        return count
    
    def count_maps_ignoring_hidden(self, maps):
        c = 0
        for map in maps:
            if map not in self.hidden_maps:
                c += 1
        return c
                
    def sort_players(self):
        self.players_data = sorted(self.players_data, key=lambda d: self.count_maps_ignoring_hidden(d['maps']['rankups']) + self.count_maps_ignoring_hidden(d['maps']['segmented']), reverse=True)
        self.save_data()
    
    def get_sorted_players_in_type(self, type: str):
        return sorted(self.players_data, key=lambda d: self.count_maps_ignoring_hidden(d['maps'][type]), reverse=True)
    
    def find_player_by_ign(self, ign: str):
        for player in self.players_data:
            if player['ign'] == ign:
                return player
            
        return None
    
    def find_player_by_user(self, user: discord.Member):
        for player in self.players_data:
            if str(player['discord_id']) == str(user.id):
                return player
            
        return None
    
    def find_player_by_id(self, id):
        for player in self.players_data:
            if str(player['discord_id']) == str(id):
                return player
            
        return None
        
    def save_data(self):
        maps_obj = json.dumps(self.maps_data, indent=4, ensure_ascii=False)
        players_obj = json.dumps(self.players_data, indent=4)
        collections_obj = json.dumps(self.collections_data, indent=4)
        
        maps_file = open('data/skillrating/maps.json', 'w', encoding='utf-8')
        players_file = open('data/skillrating/players.json', 'w')
        collections_file = open('data/skillrating/collections.json', 'w')
        
        maps_file.write(maps_obj)
        players_file.write(players_obj)
        collections_file.write(collections_obj)
        
        maps_file.close()
        players_file.close()
        collections_file.close()
        
    def load_data(self):
        maps_file = open('data/skillrating/maps.json', 'r', encoding='utf-8')     
        players_file = open('data/skillrating/players.json', 'r')
        collections_file = open('data/skillrating/collections.json', 'r')
        hidden_file = open('data/skillrating/hidden.json', 'r')
           
        maps_obj = maps_file.read()
        players_obj = players_file.read()
        collections_obj = collections_file.read()
        hidden_obj = hidden_file.read()
                
        self.maps_data = json.loads(maps_obj)   
        self.players_data = json.loads(players_obj)
        self.collections_data = json.loads(collections_obj)
        self.hidden_maps = json.loads(hidden_obj)
                     
        maps_file.close()
        players_file.close()
        collections_file.close()
        hidden_file.close()
        
    def open_spreadsheet(self):
        scope = ['https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive']
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json'
                    , scope)

    def add_property_to_all_maps(self, property, value):
        for typename, type in self.maps_data.items():
            for tier in type:
                for mapname, map in tier['maps'].items():
                    map[property] = value
                    
    def remove_property_from_all_maps(self, property):
        for typename, type in self.maps_data.items():
            for tier in type:
                for mapname, map in tier['maps'].items():
                    map.pop(property, None)
    
    def build_map_info_embeds(self, map_name: str):
        tier = self.get_map_tier(map_name)
        map = tier['maps'][map_name]
        
        embeds = []
        
        screenshot_name = map_name.lower().replace(' ', '')

        # Основная информация
        server_name = server_ip = join_instructions = is_on_pkc = "Неизвестно"
        info = map.get('info')
        if info:
            server = info.get('server')
            server_name = server.get('name')
            server_ip = server.get('ip')
            join_instructions = server.get('instructions')
            is_on_pkc = 'Да' if info.get('is_on_pkc') else 'Нет'
            
        map_type = 'Ранкап' if tier in self.maps_data['rankups'] else 'Сегментед'
        tier_name = tier['tier_name']
        
        collection_name = None
        for collection in self.collections_data:
            if map_name in collection['maps']:
                collection_name = collection['name']
        
        info_embed = discord.Embed(title=map_name)
        desc = f'**Сервер:** ```Название: {server_name}\n'
        desc += f'IP: {server_ip}\nИнструкция для входа: {join_instructions}```\n'
        desc += f'**Тип:** `{map_type}`\n\n'
        desc += f'**Тир сложности:** `{tier_name}`\n\n'
        if collection_name: desc += f'**Коллекция:** `{collection_name}`\n\n'
        desc += f'**Есть в системе очков PKC:** `{is_on_pkc}`'
        info_embed.description = desc
        info_embed.set_image(url=f'attachment://{screenshot_name}.jpg')
        info_embed.color = discord.Color.teal()
        embeds.append(info_embed)
        
        # Теги
        desc = ''
        tags_list = []
        tags = self.bot.get_cog('Tags')
        if tags != None:
            tags_list = tags.get_map_tags(map_name)
            if len(tags_list) > 0:
                desc += '**Теги:**\n'
                desc += '>>> '
                for i in range(len(tags_list)):
                    desc += f'* {tags_list[i]["name"]}\n'
                    desc += f'```{tags_list[i]["info"]}```\n'
            else:
                desc += '> У этой карты нет тегов'
        else:
            desc += '> Что-то пошло не так...'
            
        tags_embed = discord.Embed(title=map_name)
        tags_embed.description = desc
        tags_embed.color = discord.Color.teal()
        embeds.append(tags_embed)
        
        # Победители
        desc = '**Список победителей:**\n```'
        victors = map.get('victors')
        def compare_dates(a, b):
            try:
                date1 = datetime.strptime(a[1]['date'], '%d.%m.%Y')
                date2 = datetime.strptime(b[1]['date'], '%d.%m.%Y')
                
                if date1 >= date2: return 1
                else: return -1
            except:
                return -1
            
        victors = dict((x, y) for x, y in sorted(victors.items(), key=cmp_to_key(compare_dates)))
        i = 1
        for victor in victors:
            date = victors[victor]['date']
            desc += f'\n{i}. {victor} - {date}'
            i += 1
        desc += '```'
        
        victors_embed = discord.Embed(title=map_name)
        victors_embed.description = desc
        victors_embed.color = discord.Color.teal()
        embeds.append(victors_embed)
        
        # Отзывы
        desc = ''
        reviews = map.get('reviews')
        if not reviews:
            desc = '> У этой карты нет отзывов'
        else:
            for review in reviews:
                player = self.find_player_by_id(review['author'])
                desc += f'* {player["ign"]}:\n'
                desc += f'```Сложность: {review["difficulty"]}/10\n'
                desc += f'Качество: {review["quality"]}/10\n'
                desc += f'Комментарий: {review["comment"]}```\n'
        reviews_embed = discord.Embed(title=map_name)
        reviews_embed.description = desc
        reviews_embed.set_footer(text='Для создания отзыва по карте воспользуйтесь командой /map review')
        reviews_embed.color = discord.Color.teal()
        embeds.append(reviews_embed)
        
        return embeds
    
    def get_screenshot(self, map: str):
        screenshot_name = map.lower().replace(' ', '')
        if os.path.isfile(f'screenshots/{screenshot_name}.jpg'):
            return discord.File(f'screenshots/{screenshot_name}.jpg')
        return None
    
    def add_review(self, map_name, user_id, difficulty, quality, comment):
        map = self.get_map_tier(map_name)['maps'][map_name]
        reviews = map.get('reviews')
        if reviews == None:
            reviews = []
        
        for review in reviews:
            if review['author'] == user_id:
                reviews.remove(review)
                break
            
        reviews.append({'author': user_id, 'difficulty': difficulty, 'quality': quality, 'comment': comment})
        map['reviews'] = reviews
        self.save_data()
    
class Views:
    class MapInfoView(discord.ui.View):
        def __init__(self, embeds, map_name: str):
            super().__init__()
            self.embeds = embeds
            self.map_name = map_name
        
        @discord.ui.button(label="Основная информация", style=discord.ButtonStyle.green, emoji=discord.PartialEmoji.from_str('<a:book_and_quill:1190393913861754900>'))
        async def infoButton(self, interaction: discord.Interaction, button: discord.ui.Button):
            for item in self.children:
                b: discord.ui.Button = item
                b.style = discord.ButtonStyle.gray
            button.style=discord.ButtonStyle.green
            screenshot = None
            filename = f"screenshots/{self.map_name.lower().replace(' ', '')}.jpg"
            if os.path.isfile(filename):
                screenshot = discord.File(filename)
            await interaction.response.edit_message(embed=self.embeds[0], view=self, attachments = [screenshot] if screenshot is not None else utils.MISSING)
            
        @discord.ui.button(label="Теги", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji.from_str('<a:nametag:1190392905236480102>'))
        async def tagsButton(self, interaction: discord.Interaction, button: discord.ui.Button):
            for item in self.children:
                b: discord.ui.Button = item
                b.style = discord.ButtonStyle.gray
            button.style=discord.ButtonStyle.green
            await interaction.response.edit_message(embed=self.embeds[1], view=self, attachments = [])
            
        @discord.ui.button(label="Победители", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji.from_str('🏆'))
        async def victorsButton(self, interaction: discord.Interaction, button: discord.ui.Button):
            for item in self.children:
                b: discord.ui.Button = item
                b.style = discord.ButtonStyle.gray
            button.style=discord.ButtonStyle.green
            await interaction.response.edit_message(embed=self.embeds[2], view=self, attachments = [])
            
        @discord.ui.button(label="Отзывы", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji.from_str('💬'))
        async def reviewsButton(self, interaction: discord.Interaction, button: discord.ui.Button):
            for item in self.children:
                b: discord.ui.Button = item
                b.style = discord.ButtonStyle.gray
            button.style=discord.ButtonStyle.green
            await interaction.response.edit_message(embed=self.embeds[3], view=self, attachments = [])

    class ReviewEditConfirmView(discord.ui.View):
        def __init__(self, modal):
            super().__init__()
            self.modal = modal
            
        @discord.ui.button(label='Да', style=discord.ButtonStyle.primary)
        async def confirmButton(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(self.modal)
    
    class ReviewErrorView(discord.ui.View):
        def __init__(self, modal):
            super().__init__()
            self.modal = modal
            
        @discord.ui.button(label='Попробовать ещё раз', style=discord.ButtonStyle.primary)
        async def tryAgainButton(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(self.modal)
                
class Modals:
    class ReviewModal(ui.Modal, title='temp title'):
        def __init__(self, sheet: Sheet, map: str, default_difficulty='', default_quality='', default_comment=''):
            super().__init__()
            self.title = f'{map}'
            self.map = map
            self.sheet = sheet
            difficultyInput = ui.TextInput(label='Сложность в рамках этого тира, от 1 до 10:', style=discord.TextStyle.short, required=True, min_length=1, max_length=2, default=default_difficulty, custom_id='difficulty')
            qualityInput = ui.TextInput(label='Качество карты, от 1 до 10:', style=discord.TextStyle.short, required=True, min_length=1, max_length=2, default=default_quality, custom_id='quality')
            commentInput = ui.TextInput(label='Комментарий о карте', style=discord.TextStyle.long, required=False, default=default_comment, custom_id='comment')
            self.add_item(difficultyInput)
            self.add_item(qualityInput)
            self.add_item(commentInput)
        
        async def on_submit(self, interaction: discord.Interaction):
            wrong = False
            
            difficulty_input = ''
            quality_input = ''
            comment_input = ''
            
            for item in self.children:
                if item.custom_id == 'difficulty':
                    difficulty_input = item.value
                elif item.custom_id == 'quality':
                    quality_input = item.value
                elif item.custom_id == 'comment':
                    comment_input = item.value
            
            try:
                dif_num = int(difficulty_input)
                quality_num = int(quality_input)
                if dif_num < 1 or dif_num > 10 or quality_num < 1 or quality_num > 10:
                    wrong = True
            except Exception as e:
                wrong = True
            
            if wrong:
                modal = Modals.ReviewModal(self.sheet, self.map, default_difficulty=difficulty_input, default_quality=quality_input, default_comment=comment_input)
                view = Views.ReviewErrorView(modal)
                await interaction.response.send_message('```Ошибка: оценки сложности и качества должны быть цифрами от 1 до 10```', view=view, ephemeral=True)
                return
            
            self.sheet.add_review(self.map, interaction.user.id, difficulty_input, quality_input, comment_input)
            
            msg = 'Отзыв добавлен:\n'
            msg += f'```Сложность: {difficulty_input}/10\n'
            msg += f'Качество: {quality_input}/10\n'
            msg += f'Комментарий: {comment_input}```\n'
            await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Sheet(bot))