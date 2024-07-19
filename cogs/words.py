import discord
from discord import app_commands
from discord.ext import commands
import json
import asyncio
import random

class Words(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.words = {}
        self.load_words()
                
    @app_commands.command(name='words', description='Предложить пользователю сыграть в слова')
    async def words_command(self, interaction: discord.Interaction, user: discord.Member, timeout: int = 20):    
        if user.id == interaction.user.id:
            await interaction.response.send_message('Совсем одиноко?', ephemeral=True)
            return
        
        player1 = interaction.user
        player2 = user
        
        if timeout < 1 or timeout > 180:
            await interaction.response.send_message('Время для таймаута должно быть в пределах от 1 до 180 секунд', ephemeral=True)
            return
        
        await interaction.response.send_message('Приглашение создано', ephemeral=True)
        
        accept_msg = await interaction.channel.send(f'<@{user.id}>, хочешь сыграть в слова с <@{interaction.user.id}>? (время для хода {timeout} с.)')
        await accept_msg.add_reaction('✅')
        try:
            if player2.id != self.bot.user.id:
                await self.bot.wait_for('reaction_add', check=lambda reaction, user: user == player2 and str(reaction.emoji) == '✅' and reaction.message == accept_msg, timeout = 120.0)
        except asyncio.TimeoutError:
            await accept_msg.edit(content = accept_msg.content + '\nОжидание подтверждения истекло')  
        else: 
            channel = await accept_msg.create_thread(name='Игра в слова', auto_archive_duration=60)
            await channel.send(f'Игра началась! Первый ход за <@{player1.id}>')
            turn = player1.id
            running = True
            last_letter = ''
            used_words = []
            while running:
                async def do_timeout(timeout):
                    nonlocal running, turn, player1, player2, used_words

                    await asyncio.sleep(timeout)
                    
                    if turn == player1.id:
                        winner = player2.id
                    else:
                        winner = player1.id
                    msg = f'Время истекло, победил <@{winner}>!'
                    msg += f'\nВсего ходов в этой игре: {len(used_words)}'
                    await channel.send(msg)
                    
                    running = False
                    
                if not running:
                    break
            
                if last_letter == '':
                    timeout_task = asyncio.create_task(do_timeout(timeout))
                
                try:
                    if not running: 
                        timeout_task.cancel()
                        break

                    if turn == self.bot.user.id:
                        shuffled_words = random.sample(self.words[last_letter], len(self.words[last_letter]))
                        for w in shuffled_words:
                            if not w in used_words:
                                msg = await channel.send(w)  
                                break
                    else:
                        msg = await self.bot.wait_for('message', check = lambda msg: msg.author.id == turn and msg.channel == channel)
                    
                    if not running: 
                        timeout_task.cancel()
                        break
                except:
                    running = False
                else:
                    if not running: 
                        timeout_task.cancel()
                        break
                    
                    word = msg.content.lower()
                    letter = word[0]
                    words = self.words.get(letter)
                    
                    if last_letter != '' and word[0] != last_letter:
                        await channel.send(reference=msg, content=f'Тебе на {last_letter}!')
                        continue
                    
                    if not words or not word in words:
                        await channel.send(reference=msg, content='Такого слова не существует')
                        continue
                    
                    if word in used_words:
                        await channel.send(reference=msg, content='Это слово уже было использовано ранее')
                        continue
                    
                    last_ind = len(word)-1
                    while word[last_ind] in ['й', 'ь', 'ъ', 'ы']:
                        last_ind -= 1
                    last_letter = word[last_ind]
                    
                    used_words.append(word)
                        
                    await msg.add_reaction('✅')
                    if turn == player1.id:
                        turn = player2.id
                    else:
                        turn = player1.id
                    
                    timeout_task.cancel()
                    timeout_task = asyncio.create_task(do_timeout(timeout))

                    await channel.send(f'<@{turn}>, тебе на {last_letter}')
    
    @app_commands.command(name='wordsparty', description='Игра в слова на выбывание')
    async def wordsparty_command(self, interaction: discord.Interaction, timeout: int = 20):
        if timeout < 1 or timeout > 180:
            await interaction.response.send_message('Время для таймаута должно быть в пределах от 1 до 180 секунд', ephemeral=True)
            return
        
        await interaction.response.send_message('Игра создана', ephemeral=True)
        
        embed = discord.Embed(title='Игра в слова на выбывание')
        desc = 'Поставьте под этим сообщением ✅ чтобы присоединиться.'
        footer = f'Время на ход: {timeout}с.'
        embed.description = desc
        embed.set_footer(text=footer)
        accept_msg = await interaction.channel.send(embed=embed)
        await accept_msg.add_reaction('✅')
        thread = await accept_msg.create_thread(name='Ужирнённая игра в слова', auto_archive_duration=60)
        
        started = False
        async def start_game(button_interaction: discord.Interaction):
            nonlocal interaction, accept_msg, thread, started
            if started:
                await button_interaction.response.send_message('Игра уже началась', ephemeral=True)
                return
            
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message('Начать игру может только её организатор', ephemeral=True)
                return
            
            started = True
            await button_interaction.response.send_message('Игра начата')
            
            cache_msg = discord.utils.get(self.bot.cached_messages, id=accept_msg.id)
            reaction = cache_msg.reactions[0]
            users = [user async for user in reaction.users()]
            msg = f'Игра началась! Порядок участников: \n<@{interaction.user.id}>'
            players = [interaction.user.id]
            for user in users[1:]:
                if user.id != interaction.user.id:
                    players.append(user.id)
                    msg += f'\n<@{user.id}>'
                
            if len(players) <= 1:
                await button_interaction.response.send_message('Никто не присоединился :(', ephemeral=True)
                return
                    
            await thread.send(msg)
            await thread.send(f'Первый ход за <@{players[0]}>')
                    
            running = True
            turn = 0
            last_letter = ''
            used_words = []
            
            async def do_timeout(timeout):
                    nonlocal running, turn, players, used_words, last_letter

                    await asyncio.sleep(timeout)

                    sad_emoji = str(discord.utils.get(self.bot.emojis, name='sad'))
                    await thread.send(f'Время истекло, игрок <@{players[turn]}> выбывает из игры {sad_emoji}')
                    
                    players.pop(turn)
                    if turn == len(players):
                        turn = 0
                    await thread.send(f'<@{players[turn]}>, тебе на {last_letter}')
                    
                    if len(players) == 1:
                        gg_emoji = str(discord.utils.get(self.bot.emojis, name='gg'))
                        msg = f'Игрок <@{players[0]}> победил! {gg_emoji}'
                        msg += f'\nВсего ходов в этой игре: {len(used_words)}'
                        await thread.send(msg)
                        running = False
            
            while running:
                if last_letter == '':
                    timeout_task = asyncio.create_task(do_timeout(timeout))
                    
                try:
                    if not running: 
                        timeout_task.cancel()
                        break
                    m = await self.bot.wait_for('message', check = lambda msg: msg.author.id == players[turn] and msg.channel == thread)
                    if not running: 
                        timeout_task.cancel()
                        break
                except:
                    running = False
                else:
                    if not running: 
                        timeout_task.cancel()
                        break
                    
                    def replace_e(s: str):
                        s_list = list(s)
                        for i in range(len(s_list)):
                            if s_list[i] == 'ё':
                                s_list[i] = 'е'
                        return ''.join(s_list)
                    
                    word = replace_e(m.content.lower())
                    letter = word[0]
                    words = self.words.get(letter)
                    
                    if last_letter != '' and word[0] != last_letter:
                        await thread.send(reference=m, content=f'Тебе на {last_letter}!')
                        continue
                    
                    if not words or not word in words:
                        await thread.send(reference=m, content='Такого слова не существует')
                        continue
                    
                    if word in used_words:
                        await thread.send(reference=m, content='Это слово уже было использовано ранее')
                        continue
                    
                    last_ind = len(word)-1
                    while word[last_ind] in ['й', 'ь', 'ъ', 'ы']:
                        last_ind -= 1
                    last_letter = word[last_ind]
                    used_words.append(word)
                    
                    await m.add_reaction('✅')
                    turn += 1
                    if turn == len(players): turn = 0
                    
                    timeout_task.cancel()
                    timeout_task = asyncio.create_task(do_timeout(timeout))
                    
                    if not running: 
                        timeout_task.cancel()
                        break
                    await thread.send(f'<@{players[turn]}>, тебе на {last_letter}')
            
        view = discord.ui.View()
        button = discord.ui.Button(label='Начать игру', style=discord.ButtonStyle.green)
        view.add_item(button)
        await thread.send('Игроки будут ходить по очереди, до тех пор пока не останется один победитель. Игра начнётся когда организатор нажмёт на кнопку.', view=view)
        button.callback = start_game
    
    def load_words(self):
        file = open('data/words.json', 'r', encoding='cp1251')
        json_obj = file.read()
        self.words = json.loads(json_obj)
        file.close()
        
        
async def setup(bot):
    await bot.add_cog(Words(bot))