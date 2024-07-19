from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import myutils
import time
import datetime

class Servers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.servers = []
        self.load_data()
    
    @app_commands.command(name='createserversmsg')
    async def create_msg(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if interaction.user.id != 269105396587823104:
            await interaction.response.send_message('не-а', ephemeral=True)
            return
        view = ServersView()
        await channel.send(embed=self.build_servers_embed(), view=view)
        await interaction.response.send_message('Сообщение создано', ephemeral=True)
        
    def build_servers_embed(self):
        embed = discord.Embed(title='Статус серверов', color=discord.Color.green())
        desc = ''
        desc += f'Для обновления нажмите кнопку под этим сообщением.\n'
        timestamp = int(time.time())-1
        desc += f'Последнее обновление: <t:{timestamp}:R>\n'
        for server in self.servers:
            server_status = myutils.get_server_status(server['ip'])
            desc += f'\n> **{server["name"]}**\n'
            desc += f'> IP: ``{server["ip"]}``\n'
            status = 'Онлайн 🟢' if server_status['online'] else 'Оффлайн 🔴'
            desc += f'> Статус: ``{status}``\n'
            if server_status['online']:
                desc += f'> Игроки: ``{server_status["players"]["online"]}/{server_status["players"]["max"]}``\n'
            else:
                desc += f'> Игроки: ``0/0``\n'    
            
        embed.description = desc
        embed.set_footer(text='Обновление может занять несколько секунд')
        return embed
        
    def load_data(self):
        file = open('data/servers.json', 'r')
        json_obj = file.read()
        self.servers = json.loads(json_obj)
        file.close()
        
class ServersView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label='Обновить', style=discord.ButtonStyle.blurple, custom_id='update_button')
    async def update(self, interaction: discord.Interaction, button: discord.ui.Button):
        servers = interaction.client.get_cog('Servers')
        if servers == None:
            await interaction.response.send_message('Ошибка при обновлении', ephemeral=True)
            return
        
        await interaction.response.defer()
        
        embed = servers.build_servers_embed()
        await interaction.message.edit(content='', embed=embed)

async def setup(bot):
    await bot.add_cog(Servers(bot))