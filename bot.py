import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord import utils
import myutils
import typing
import os.path
import accounts
import datetime
import random
import cogs.servers
from roles import main_roles, plus_roles
from emojis import Emojis

TOKEN = 'РЕДАКТЕД'

class MPRU_Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='=', intents=intents)
        
    async def setup_hook(self) -> None:
        self.add_view(cogs.servers.ServersView())
        
bot = MPRU_Bot()

@bot.event
async def on_message(msg):
	if msg.author.bot:
		return

	if bot.user.mentioned_in(msg) or msg.content.lower().startswith('='):
		if (msg.content.lower().endswith(' gm') or ' gm ' in msg.content.lower() or '=gm' in msg.content.lower()):
			gm = bot.get_cog('GM')
			if gm is not None:
				await gm.gm_command(msg)
		elif (msg.content.endswith (' gn') or ' gn ' in msg.content.lower()):
			await msg.channel.send(content='||кто прочитал тот лох||')
		elif (msg.content.endswith('q')):
			quotes = bot.get_cog('Quotes')
			if quotes is not None:
				await quotes.quote(msg.channel)
   
	levels = bot.get_cog('Levels')
	if levels:
		await levels.give_xp(msg.author.id)
        
@bot.event
async def on_ready():
	try:
		for f in os.listdir("./cogs"):
			if f.endswith(".py"):
				await bot.load_extension("cogs." + f[:-3])

		synced = await bot.tree.sync()
		print(f'Synced {len(synced)} command(s)')
  
		roles = bot.get_cog('Roles')
		if roles:
			await roles.load_roles()
 
		polls = bot.get_cog('Polls')
		if polls:
			await polls.load_data()

	except Exception as e:
		print(e)

def init():  
	bot.run(TOKEN)