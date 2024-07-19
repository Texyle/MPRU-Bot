import discord
from discord.ext import commands
from discord import app_commands
import requests
import json

class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tags = {}
        self.load_tags()
    
    group = app_commands.Group(name='tag', description="Команды связанные с тегами")
    
    @group.command(name='reload', description='Загружает данные из таблицы тегов в бота')
    async def reload(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.load_tags()
        await interaction.followup.send('Теги перезагружены')
        
    def load_tags(self):
        self.tags = {}
        
        spreadsheet_id = '1DaA4u1ybNF0Vb50vu_X-XUrpdvf12pvKCoNucdV1XSc'
        credentials = self.bot.get_cog('Sheet').credentials
        
        fields = "sheets.data.rowData.values.userEnteredValue.stringValue"
        range_maps = "'Map Tags'!C4:F"
        range_rankups = "'Rankup Tags'!C4:F38"
        
        res = requests.get('https://sheets.googleapis.com/v4/spreadsheets/' + spreadsheet_id + f"?includeGridData=true&fields={fields}&ranges={range_maps}&ranges={range_rankups}",
                                headers={"Authorization": "Bearer " + credentials.get_access_token().access_token, "Content-Type": "application/json"},
                                data={})  
        
        sheets = res.json().get('sheets')
        maps_sheet = sheets[0]
        rankup_sheet = sheets[1]
        
        map_list = self.bot.get_cog('Sheet').get_map_list()
        
        # Load maps sheet
        data = maps_sheet.get('data')[0].get('rowData')
        last_map = ''
        for row in data:
            values = row.get('values')
            
            try:
                map_name = values[0].get('userEnteredValue').get('stringValue')
            except:
                map_name = last_map
            last_map = map_name
                        
            if map_name.lower() not in map(str.lower, map_list):
                    continue
            
            tag_name = tag_id = tag_info = 'Неизвестно'
            try:
                tag_name = values[1].get('userEnteredValue').get('stringValue')
                tag_id = values[2].get('userEnteredValue').get('stringValue')
                tag_info = values[3].get('userEnteredValue').get('stringValue')
            except:
                continue
                
            self.tags[tag_id] = {'name': tag_name, 'map': map_name, 'info': tag_info}
            
        # Load rankup sheet
        data = rankup_sheet.get('data')[0].get('rowData')
        last_map = ''
        for row in data:
            values = row.get('values')
            try:
                bonus_name_pro = f'Linkcraft Bonus {values[0].get("userEnteredValue").get("stringValue")} Pro'
                if bonus_name_pro.lower() in map(str.lower, map_list):
                    bonus_name_normal = f'Linkcraft Bonus {values[0].get("userEnteredValue").get("stringValue")} Normal'
                    tag_name = values[1].get('userEnteredValue').get('stringValue')
                    tag_id = values[2].get('userEnteredValue').get('stringValue')
                    tag_info = values[3].get('userEnteredValue').get('stringValue')
                    self.tags[tag_id+'_pro'] = {'name': tag_name, 'map': bonus_name_pro, 'info': tag_info}
                    self.tags[tag_id+'_normal'] = {'name': tag_name, 'map': bonus_name_normal, 'info': tag_info}
                    last_map = map_name
                    continue
                
                map_name = "Linkcraft " + values[0].get('userEnteredValue').get('stringValue')
                if map_name.lower() not in map(str.lower, map_list):
                    last_map = map_name
                    continue
                                
            except:
                map_name = last_map
            last_map = map_name
            
            tag_name = tag_id = tag_info = 'Неизвестно'
            try:
                tag_name = values[1].get('userEnteredValue').get('stringValue')
                tag_id = values[2].get('userEnteredValue').get('stringValue')
                tag_info = values[3].get('userEnteredValue').get('stringValue')
            except:
                continue
            
            self.tags[tag_id] = {'name': tag_name, 'map': map_name, 'info': tag_info}
        
    def get_map_tags(self, map_name):
        tags = []
        for tag_id, tag in self.tags.items():
            if tag['map'].lower() == map_name.lower():
                tags.append(tag)
        return tags
            
async def setup(bot):
    await bot.add_cog(Tags(bot))