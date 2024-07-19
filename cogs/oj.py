import discord
from discord.ext import commands
from discord import app_commands, utils
import json

class OJ(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ojs_data = None
        self.load_data()
        
    group = app_commands.Group(name='oj', description="Команды связанные с ванджампами")
    
    @group.command(name='announce', description='Сделать оповещения о прохождении игроком прыжка')
    async def announce(self, interaction: discord.Interaction, player: discord.User, jump_id: int, clip: discord.Attachment):
        allowed = False
        for role in interaction.user.roles:
            if role.name == "Админ" or role.name == "Хелпер":
                allowed = True    
        
        if not allowed:
            await interaction.response.send_message(f'А тебе низя :/', ephemeral=True)
            return
        
        jump = self.ojs_data.get(str(jump_id))
        if not jump:
            await interaction.response.send_message(f'Прыжок с номером {jump_id} не найден', ephemeral=True)
            return
        
        gg_emoji = str(discord.utils.get(self.bot.emojis, name='gg'))
        embed = discord.Embed(title=f'{gg_emoji}{gg_emoji}{gg_emoji}', color=discord.Color.yellow())
        
        desc = f'Поздравляем игрока <@{player.id}> с прохождением прыжка\n**{jump_id} - {jump.get("name")} ({jump.get("difficulty")})**'
        embed.description = desc
                
        await interaction.response.defer(ephemeral=True)     
                
        file = utils.MISSING
        if clip:
            file = await clip.to_file()
        
        mpru_guild = self.bot.get_guild(1041059132448444509)
        announce_channel = mpru_guild.get_channel(1200697432909029439)
        ping_role_id = 1139465950249361418
            
        ping_msg = ''
        if jump.get("difficulty") in ['D10', 'D11']:
            role = utils.get(mpru_guild.roles, id=ping_role_id)
            ping_msg = f'{role.mention}'
            
        await announce_channel.send(content=ping_msg, embed=embed, file=file)
        await interaction.followup.send(f'Успех', ephemeral=True)   
    
    @group.command(name='add', description='Добавить информацию о прыжке в базу данных')
    async def add(self, interaction: discord.Interaction, hpk_id: str, full_name: str, difficulty: str):
        allowed = False
        for role in interaction.user.roles:
            if role.name == "Админ" or role.name == "Хелпер":
                allowed = True    
        
        if not allowed:
            await interaction.response.send_message(f'А тебе низя :/', ephemeral=True)
            return   
        
        self.ojs_data[hpk_id] = {'name': full_name, 'difficulty': difficulty}
        
        self.save_data()
        
        await interaction.response.send_message(f'{hpk_id}: {full_name} ({difficulty})', ephemeral=True)
        
    def load_data(self):
        file = open('data/ojs.json', 'r')     
        obj = file.read()
        self.ojs_data = json.loads(obj)        
        file.close()

    def save_data(self):
        obj = json.dumps(self.ojs_data, indent=4)
        file = open('data/ojs.json', 'w')
        file.write(obj)
        file.close()
    
async def setup(bot):
    await bot.add_cog(OJ(bot))