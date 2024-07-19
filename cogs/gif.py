import discord
from discord.ext import commands
from discord import app_commands
import myutils

class GIF(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name='randomgif')
    async def randomgif(self, interaction: discord.Interaction, query: str=''):
        embed = discord.Embed(title="Рандомная гифка")
        if len(query) == 0:
            embed.description = f'Запрос: N/A'
        else:
            embed.description = f'Запрос: {query}'
            
        embed.set_image(url=myutils.search_gif(query))
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(GIF(bot))