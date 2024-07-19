import discord
from discord.ext import commands
from discord import app_commands

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles = {}
        
    @commands.Cog.listener()
    async def on_member_join(self, member):
        member.add_roles(self.roles['Новичок'], reason='First time join')
        
    async def load_roles(self):
        mpru_guild = self.bot.get_guild(1041059132448444509)
        roles = mpru_guild.roles
        
        for role in roles:
            if role.name == 'Новичок':
                self.roles['Новичок'] = role
        
async def setup(bot):
    await bot.add_cog(Roles(bot))