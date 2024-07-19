import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import json
import random
import myutils
import datetime

reset_time = datetime.time(hour=21, minute=00, tzinfo=datetime.timezone.utc)

class GM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.users = {}
        self.load()
        self.reset.start()
        
    group = app_commands.Group(name='gm', description='Утро начинается не с кофе')
        
    @group.command(name='top', description='Топ пользователей по количеству ГМов')
    async def gmtop(self, interaction: discord.Interaction):
        self.sort()
        msg = ''
        i = 1
        for id, data in self.users.items():
            if data['count'] == 0:
                continue
            
            msg += f"\n**{i}.** <@{id}>: {data['count']} ({data['count']-data['bonus']}+{data['bonus']})"
            i += 1
                	
        embed = discord.Embed(title="Топ по GM", description=msg)
        await interaction.response.send_message(embed=embed)
    
    @group.command(name='offer', description='Создать запрос на передачу ГМов другому пользователю')
    async def offer(self, interaction: discord.Interaction, receiver: discord.Member, amount: int, comment: str):
        sender_profile = self.get_user(interaction.user.id)
        receiver_profile = self.get_user(receiver.id)
        
        if interaction.user.id == receiver.id:
            await interaction.response.send_message('Зачем?', ephemeral=True)
            return
        elif sender_profile == None or sender_profile['count'] < amount:
            await interaction.response.send_message('У тебя не хватает ГМов :(', ephemeral=True)
            return
        elif amount <= 0:
            await interaction.response.send_message('Неверно введённая сумма', ephemeral=True)
            return
        
        embed = discord.Embed(title='Передача ГМов')
        msg = f'Отправитель: <@{interaction.user.id}>\nСумма: {amount}\nКомментарий отправителя: ``{comment}``'
        msg += '\n\nДля подтверждения получатель должен поставить реакцию ✅ на это сообщение'
        embed.description = msg
        
        offer_msg = await  interaction.channel.send(content = f'<@{receiver.id}>', embed=embed)
        await offer_msg.add_reaction('✅')
        
        await interaction.response.send_message('Запрос отправлен', ephemeral=True)
        
        def check(reaction, user):
            return user == receiver and str(reaction.emoji) == '✅' and reaction.message == offer_msg
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=3600.0, check=check)
        except asyncio.TimeoutError:
            await offer_msg.channel.send(reference = offer_msg, content='Ожидание подтверждения истекло')
        else:
            if receiver_profile == None:
                receiver_profile = self.register_user(receiver_profile)
             
            if sender_profile['count'] < amount:
                await offer_msg.channel.send(reference = offer_msg, content='Что-то пошло не так...')
             
            sender_profile['count'] -= amount
            receiver_profile['count'] += amount
            
            await offer_msg.channel.send(reference = offer_msg, content='Сделка прошла успешно')
        
    @group.command(name='forcereset', description='На случай если ресет в 00:00 не сработал')
    async def force_reset(self, interaction: discord.Interaction):
        if interaction.user.id != 269105396587823104:
            await interaction.response.send_message('не-а', ephemeral=True)
            return   
        
        await self.reset()
        await interaction.response.send_message('готово', ephemeral=True)
    
    @group.command(name='gif', description='Установить запрос для гифок в ответном сообщении бота')
    async def gif_command(self, interaction: discord.Interaction, query: str):
        profile = self.get_user(interaction.user.id)
        if profile == None or profile['count'] < 100:
            await interaction.response.send_message('Эта функция доступна только после 100 ГМов', ephemeral=True)
            return
        
        profile['custom_query'] = query
        await interaction.response.send_message(f'Теперь при поиске гифок в ответном сообщении бота будет использован запрос ``{query}``', ephemeral=True)
                      
    async def gm_command(self, msg):
        user = self.get_user(msg.author.id)
        
        if user == None:
            user = self.register_user(msg.author.id)
            
        if user['done']:
           embed = discord.Embed(description='Ты уже забрал свой ГМ сегодня! (Обновляется в 00:00 по МСК)', color=discord.Color.red())
           await msg.channel.send(reference=msg, embed=embed)
           return
       
        embed = discord.Embed(title='Good morning!', color=discord.Color.yellow())
        desc = ''
       
        guess = 1
        guessed = False
        for word in msg.content.split():
            try:
                num = int(word)
                if num >= 1 and num <= 1000:
                    guess = num
                    guessed = True
                    break
            except ValueError:
                continue
                
        rand = random.randint(1, 1000)       
        bonus = 0
        diff = abs(rand - guess)
        
        if guessed:
            desc += f'Загаданное число: {rand} (разница {diff})\n'
            
        if (diff == 0):
            desc += '💥💥💥🤯🤯🤯🤑🤑🤑\nжёско зароллил 0.1% и получил 10 гмов!!!!!!!!!\n💥💥💥🤯🤯🤯🤑🤑🤑\n\n'
            embed.color = discord.Color.pink()
            bonus = 9
        elif (diff <= 5):
            desc += 'нифигасеафигеть, держи 5 гмов 👏\n\n'
            embed.color = discord.Color.orange()
            bonus = 4
        elif (diff <= 50):
            desc += 'Сегодня твой день, получай сразу 2 ГМа 😎\n\n'
            embed.color = discord.Color.gold()
            bonus = 1
        
        user['count'] += bonus + 1
        user['bonus'] += bonus
        user['done'] = True
        self.save()

        c = user['count']
        desc += f'Твой счёт: {c}'
        
        embed.description = desc
        query = user.get('custom_query') or 'good morning'
        embed.set_image(url=myutils.search_gif(query))
        await msg.channel.send(reference=msg, embed=embed)
    
    def get_user(self, id):
        return self.users.get(str(id))
    
    def register_user(self, id):
        self.users[str(id)] = {'count': 0, 'bonus': 0, 'done': False}
        return self.users[str(id)]
    
    def load(self):
        f = open('data/gmusers.json', 'r')
        json_obj = f.read()
        self.users = json.loads(json_obj)
        
    def save(self):
        self.sort()
        json_obj = json.dumps(self.users, indent=4)
        f = open('data/gmusers.json', 'w')
        f.write(json_obj)
        
    def sort(self):
        self.users = dict(sorted(self.users.items(), key = lambda x:x[1]['count'], reverse=True))
    
    @tasks.loop(time=reset_time)
    async def reset(self):
        for id in self.users:
            self.users.get(id)['done'] = False
        self.save()
        
async def setup(bot):
    await bot.add_cog(GM(bot))