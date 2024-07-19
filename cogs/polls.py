import discord
from discord.ext import commands
from discord import app_commands
import json

number_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

class Polls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        mpru_guild = self.bot.get_guild(1041059132448444509)
        self.poll_channel = mpru_guild.get_channel(1185675409069711372)
        self.polls = []
    
    @app_commands.describe(question='Вопрос который будет отображаться в опросе',
                           options='Варианты ответа на опрос. Разделяются точками с запятой (;). Эмодзи с цифрами писать не надо, они будут присвоены автоматически.',
                           show_author='Показывать ли ваш ник в названии опроса.',
                           anonimous='Если true, то в опросе не будет показываться проголосовавшие пользователи.')
    @app_commands.command(name='createpoll', description='Создать опрос')
    async def createpoll_command(self, interaction: discord.Interaction, question: str, options: str, show_author: bool, anonimous: bool):
        option_list = options.split(';')
        if len(option_list) <= 1:
            await interaction.response.send_message('```В опросе должно быть больше одного варианта ответа.```', ephemeral=True)
            return
        
        if len(option_list) > 10:
            await interaction.response.send_message('```В опросе не может быть больше десяти вариантов ответа.```', ephemeral=True)
            return
        
        for option in option_list:
            if option[0] == ' ':
                option = option[1:]
            if len(option) > 100:
                await interaction.response.send_message('```Вариант ответа не может превышать 100 символов в длину```', ephemeral=True)
                return
        
        author = interaction.user if show_author else None
        poll = Poll(question, option_list, anonimous, len(self.polls)+1)
        poll.create_embed(author)
        msg = await self.poll_channel.send(embed=poll.embed)
        poll.msg_id = msg.id
        self.polls.append(poll)
        self.save_data()
        
        await interaction.response.send_message(f'Опрос создан: {msg.jump_url}', ephemeral=True)
        for i in range(len(option_list)):
            await msg.add_reaction(number_emojis[i])
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id != self.poll_channel.id:
            return
        
        poll = self.get_poll_by_msg(payload.message_id)
        if poll == None:
            return
        
        if not str(payload.emoji) in number_emojis:
            return
        
        user = payload.member
        option = number_emojis.index(str(payload.emoji))
        
        if user.bot:
            return
        
        if poll.anonimous:
            for o in poll.votes:
                if user.id in o:
                    o.remove(user.id)
        
        if not user.id in poll.votes[option]: poll.votes[option].append(user.id)
        
        msg = await self.poll_channel.fetch_message(payload.message_id)
        poll.embed.description = poll.build_description()
        await msg.edit(embed = poll.embed)
            
        if poll.anonimous:
            await msg.remove_reaction(payload.emoji, user)
            
        self.save_data()
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):        
        poll = self.get_poll_by_msg(payload.message_id)
        if poll == None:
            return
        
        if not str(payload.emoji) in number_emojis:
            return
        
        option = number_emojis.index(str(payload.emoji))
        
        msg = await self.poll_channel.fetch_message(payload.message_id)
        if msg.channel.id != self.poll_channel.id:
            return
        
        poll = self.get_poll_by_msg(payload.message_id)
        
        if poll == None or poll.anonimous:
            return
        
        option = number_emojis.index(str(payload.emoji))       
        if payload.user_id in poll.votes[option]: 
            poll.votes[option].remove(payload.user_id)
        poll.embed.description = poll.build_description()
        await msg.edit(embed = poll.embed)  
        
        self.save_data()
        
    def get_poll_by_msg(self, msg_id):
        for poll in self.polls:
            if poll.msg_id == msg_id:
                return poll
        return None
    
    def save_data(self):
        def default(o):
            if isinstance(o, discord.Embed):
                return {'name': o.author.name, 'icon_url': o.author.icon_url}
            else:
                return json.JSONEncoder.default(self, o)
        
        json_string = json.dumps([ob.__dict__ for ob in self.polls], indent=4, default=default)
        file = open('data/polls.json', 'w', encoding='utf-8')
        file.write(json_string)
        file.close()
        
    async def load_data(self):
        file = open('data/polls.json', 'r', encoding='utf-8')
        json_string = file.read()
        json_obj = json.loads(json_string)
        for json_poll in json_obj:
            msg_id = json_poll['msg_id']
            poll = Poll(json_poll['question'], json_poll['options'], json_poll['anonimous'], json_poll['index'])
            poll.msg_id = msg_id
            poll.votes = json_poll['votes']
            poll.embed.set_author(name=json_poll['embed']['name'], icon_url=json_poll['embed']['icon_url'])
            self.polls.append(poll)

class Poll:
    def __init__(self, question: str, options: list, anonimous: bool, index: int):
        self.question = question
        self.options = options
        self.msg_id = 0
        self.votes = [[] for o in options]
        self.anonimous = anonimous
        self.index = index
        an = ' (Анонимный)' if anonimous else ''
        self.embed = discord.Embed(title=f'Опрос #{self.index}{an}', color=discord.Color.yellow())
    
    def create_embed(self, author = None):
        an = ' (Анонимный)' if self.anonimous else ''
        self.embed = discord.Embed(title=f'Опрос #{self.index}{an}', color=discord.Color.yellow())
        if author:
            self.embed.set_author(name=author.display_name, icon_url=author.avatar.url)
        else:
            self.embed.set_author(name='Аноним')
            
        self.embed.description = self.build_description()
    
    def build_description(self):
        desc = f'{self.question}\n'
        total_votes = sum([len(x) for x in self.votes])
        for i in range(len(self.options)):
            desc += f'\n{number_emojis[i]} - {self.options[i]}'
            percentage = int(len(self.votes[i])/total_votes*100) if total_votes != 0 else 0
            desc += f'\n{percentage}% - {len(self.votes[i])} голос(ов)'
        return desc
        
async def setup(bot):
    await bot.add_cog(Polls(bot))