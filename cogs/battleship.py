import discord
from discord.ext import commands
from discord import app_commands
from asyncio import gather
from enum import Enum
import random
import asyncio
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

class Orientation(Enum):
    HORIZONTAL = (0, 1)
    VERTICAL = (1, 0)

class Coordinates(Enum):
    COLUMNS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    ROWS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']

class Field:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.ships = {1: [], 2: [], 3: [], 4: []}
        self.attacked_cells = set()
        
    def generate(self):
        self.ships = {1: [], 2: [], 3: [], 4: []}
        
        # 0 -> empty; 
        # 1 -> ship; 
        # 2 -> near ship
        field_arr = [[0 for i in range(10)] for i in range(10)]
        ships_amount = [4, 3, 2, 1]
        
        def available(row, column, size, orientation):
            for i in range(size):
                if field_arr[row][column] != 0:
                    return False
                row += orientation.value[0]
                column += orientation.value[1]
                if row >= self.height or column >= self.width:
                    return False
            return True
        
        for size in range(1, 5):
            amount = ships_amount[size-1]
            
            for i in range(amount):
                o = random.randint(1, 2)
                orientation = Orientation.HORIZONTAL if o == 1 else Orientation.VERTICAL
            
                available_places = [(row, column) for row in range(len(field_arr)) for column in range(len(field_arr[row])) if available(row, column, size, orientation)]
                if len(available_places) == 0:
                    orientation = Orientation.HORIZONTAL if o == 2 else Orientation.VERTICAL
                    available_places = [(row, column) for row in range(len(field_arr)) for column in range(len(field_arr[row])) if available(row, column, size, orientation)]
                    if len(available_places) == 0:
                        return self.generate()
                
                random_place = random.choice(available_places)
                
                cell = [random_place[0], random_place[1]]
                for j in range(size):
                    field_arr[cell[0]][cell[1]] = 1
                    for k in range(-1, 2):
                        for l in range(-1, 2):
                            i_ind = cell[0] + l
                            j_ind = cell[1] + k
                            if i_ind < 0 or i_ind >= self.height: continue
                            if j_ind < 0 or j_ind >= self.width: continue
                            
                            if field_arr[i_ind][j_ind] != 1: field_arr[i_ind][j_ind] = 2 

                    cell[0] += orientation.value[0]
                    cell[1] += orientation.value[1]
            
                ship = Ship(random_place, size, orientation)
                self.ships[size].append(ship)
    
    def attack(self, cell: tuple):
        # -2 -> wrong coords
        # -1 -> already attacked
        #  0 -> missed ship
        #  1 -> hit ship
        #  2 -> destroyed ship
        
        if cell[0] < 0 or cell[0] >= self.width or cell[1] < 0 or cell[1] >= self.height:
            return -2, None
        
        if cell in self.attacked_cells:
            return -1, None
        
        self.attacked_cells.add(cell)
        
        hit_ship = None
        err = 0
        for ship_type in self.ships.values():
            for ship in ship_type:
                if cell in ship.cells:
                    err = ship.hit(cell)
                    hit_ship = ship
                    break
                    
        if err == 2:
            for cell in hit_ship.cells:
                self.attacked_cells.add(cell)
                for k in range(-1, 2):
                    for l in range(-1, 2):
                        i_ind = cell[0] + l
                        j_ind = cell[1] + k
                        if i_ind < 0 or i_ind >= self.height: continue
                        if j_ind < 0 or j_ind >= self.width: continue
                        self.attacked_cells.add((i_ind, j_ind))
            
        return err
     
    def alive_ships_count(self):
        count = 0
        
        for ship_type in self.ships.values():
            for ship in ship_type:
                if not ship.destroyed:
                    count += 1
                    
        return count
        
    def valid_location(self, location, orientation, length):
        if location[0] + length * orientation.value[0] > self.width:
            return False
        if location[1] + length * orientation.value[1] > self.height:
            return False
        
        for ship_type in self.ships.values():
            for ship in ship_type:
                if ship.is_touching(location, orientation, length):
                    return False
        
        return True
    
    def is_valid(self):
        if len(self.ships[1]) != 4 or len(self.ships[2]) != 3 or len(self.ships[3]) != 2 or len(self.ships[4]) != 1:
            return False
        
        for ship_type in self.ships.values():
            for ship in ship_type:
                if ship.location[0] < 0 or ship.location[1] < 0:
                    return False
                if ship.location[0] > self.height or ship.location[1] > self.width:
                    return False 
                for ship_type_ in self.ships.values():
                    for other in ship_type_:
                        if ship == other:
                            continue
                        if ship.is_touching_ship(other):
                            return False
        
        return True
    
    def build_image(self, show_ships = False):
        size = 300
        bg_color = (150, 150, 150, 255)
        image = Image.new('RGBA', (size, size), bg_color)
        draw = ImageDraw.Draw(image)
        
        line_color = (0, 0, 0, 255)
        text_color = (0, 0, 0, 255)
        cross_color = (120, 120, 120, 255)
        hit_cross_color = (255, 0, 0, 255)
        grid_color = (255, 255, 255, 255)
        destroyed_ship_color = (80, 80, 80, 255)
        destroyed_ship_outline_color = (0, 0, 0, 255)
        
        # Grid
        step = size / 12
        
        draw.rectangle((step, step, size-step+2, size-step+2), fill=grid_color)
        
        for i in range(1, 12):
            coord = i*step
            width = 2
            start = step
            if i == 1 or i == 11:
                width = 4
            offset = width/2
            draw.line((coord, start-offset+1, coord, size-start+offset*2-2), fill=line_color, width=width)
            draw.line((start-offset+1, coord, size-start+offset*2-2, coord), fill=line_color, width=width)
            
        # Coordinates
        font = ImageFont.truetype('data/fonts/Geist-Black.otf', 16)
        for i in range(10):
            coord = (i+1)*step+step/2+2
            draw.text((coord, 19), Coordinates.COLUMNS.value[i], font=font, fill=text_color, anchor='mb')
            draw.text((13, coord), Coordinates.ROWS.value[i], font=font, fill=text_color, anchor='mm')
                
        # Ships
        offset = 4
        for ship_type in self.ships.values():
            for ship in ship_type:
                if ship.destroyed or show_ships:
                    cells = ship.cells
                    x1 = (cells[0][1] + 1) * step + offset 
                    y1 = (cells[0][0] + 1) * step + offset
                    x2 = (cells[len(cells)-1][1] + 1) * step + step - offset + 1
                    y2 = (cells[len(cells)-1][0] + 1) * step + step - offset + 1
                    
                    draw.rectangle((x1, y1, x2, y2), fill=destroyed_ship_color, outline=destroyed_ship_outline_color, width=2)
        
        # Crosses
        hit_ship_cells = []
        for ship_type in self.ships.values():
            for ship in ship_type:
                for index in ship.hit_cells:
                    hit_ship_cells.append(ship.cells[index])
        
        for cell in self.attacked_cells:
            x = (cell[1] + 1) * step
            y = (cell[0] + 1) * step
            
            offset = step/5 + 1
            
            if cell in hit_ship_cells:
                color = hit_cross_color
            else:
                color = cross_color
            
            draw.line((x+offset, y+offset, x+step-offset, y+step-offset), fill=color, width=2)
            draw.line((x+offset, y+step-offset, x+step-offset, y+offset), fill=color, width=2)
        
        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            return discord.File(fp=image_binary, filename='image.png')
            
    def __str__(self):
        arr = [['▯' for i in range(10)] for j in range(10)]
        for ship_type in self.ships.values():
            for ship in ship_type:
                for cell in ship.cells:
                    arr[cell[0]][cell[1]] = '▮'
                    
        string = ''.join(arr[0])
        for i in range(len(arr)-1):
            string += '\n' + ''.join(arr[i+1])
            
        return string
    
    def __repr__(self):
        return str(self.ships)
              
class Ship:
    def __init__(self, location: tuple, length: int, orientation: Orientation):
        self.location = location
        self.length = length
        self.orientation = orientation
        self.cells = []
        self.hit_cells = []
        self.calculate_cells()
        self.destroyed = False
    
    def hit(self, cell):
        # -2 -> wrong coords
        # -1 -> already hit
        #  1 -> hit but not destroyed
        #  2 -> hit and destroyed
        
        if cell not in self.cells:
            return -2
        
        if cell in self.hit_cells:
            return -1
        
        self.hit_cells.append(self.cells.index(cell))
        
        if len(self.hit_cells) < len(self.cells):
            return 1
        else:
            self.destroyed = True
            return 2
    
    def calculate_cells(self):
        for i in range(0, self.length):
            i_coord = self.location[0] + i*self.orientation.value[0]
            j_coord = self.location[1] + i*self.orientation.value[1]
            self.cells.append((i_coord, j_coord))
        
    def is_touching_ship(self, other):
        return self.is_touching(other.location, other.orientation, other.length)
    
    def is_touching(self, location, orientation, length):
        this_cell = [self.location[0], self.location[1]]
        
        for i in range(self.length):
            other_cell = [location[0], location[1]]
            for j in range(length):
                dist_i = abs(this_cell[0] - other_cell[0])
                dist_j = abs(this_cell[1] - other_cell[1])
                
                if dist_i * dist_j <= 1 and dist_j < 2 and dist_i < 2:
                    return True
                
                other_cell[0] += orientation.value[0]
                other_cell[1] += orientation.value[1]
            
            this_cell[0] += self.orientation.value[0]
            this_cell[1] += self.orientation.value[1]
            
        return False
    
    def __repr__(self):
        return f'(Location: {self.location}, Length: {self.length}, Orientation: {self.orientation})'

class Battleship(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ships_required = [1, 2, 3, 4]
        
    @app_commands.command(name='battleship', description='Предложить пользователю сыграть в морской бой')
    async def battleship_command(self, interaction: discord.Interaction, user: discord.Member):
        if user.id == interaction.user.id:
            await interaction.response.send_message('совсем одиноко?', ephemeral=True)
            return
        
        await interaction.response.send_message('👍', ephemeral=True)
        
        player1 = interaction.user
        player2 = user
        
        accept_msg = await interaction.channel.send(f'<@{user.id}>, хочешь сыграть в морской бой с <@{interaction.user.id}>?')
        await accept_msg.add_reaction('✅')
        
        try:
            if player2.id != self.bot.user.id:
                await self.bot.wait_for('reaction_add', check=lambda reaction, user: user == player2 and str(reaction.emoji) == '✅' and reaction.message == accept_msg, timeout = 120.0)
        except asyncio.TimeoutError:
            await accept_msg.edit(content = accept_msg.content + '\nОжидание подтверждения истекло')  
        else: 
            thread = await accept_msg.create_thread(name='Морской бой', auto_archive_duration=60)
            
            # instructions
            instructions_embed = discord.Embed(title='Как играть', color=discord.Color.blue())
            desc = f'Для начала игроки должны расставить корабли в личных сообщениях с ботом.' 
            desc += f'После этого в канал {accept_msg.channel.jump_url} будет отправлены два сообщения с изображениями игровых полей для обоих игроков, которые будут обновляться после каждого хода соответствующего игрока.'
            desc += f'\n\nВ этой ветке игроки поочерёдно будут писать координаты клетки, которую хотят атаковать (например A1, B2, C3...). Игра закончится, когда один из игроков уничтожит все корабли противника.'
            instructions_embed.description = desc
            instructions_embed.set_footer(text='Если что в дискорде можно менять размер открытой на экране ветки')
            await thread.send(embed=instructions_embed)

            fields = await gather(self.place_ships(player1), self.place_ships(player2))
            #field1 = Field(10, 10)
            #field1.generate()
            #field2 = Field(10, 10)
            #field2.generate()
            #fields = [field1, field2]
            
            await thread.send('Оба игрока расставили корабли, игра начинается!')
            
            await self.game_loop(thread, [player1, player2], fields[::-1])
    
    async def game_loop(self, thread: discord.Thread, players: list, fields: list):
        if len(fields) != 2: return
        
        field_messages = [None, None]
        
        for i in range(2):
            field_messages[i] = await thread.parent.send(content=f'<@{players[i].id}>, поле твоего соперника:', file=fields[i].build_image())
            
        playing = True
        turn = 0
        await thread.send(f'Первый ход за <@{players[0].id}>')
        while playing:
            if players[turn].id == self.bot.user.id:
                coord1 = random.choice(Coordinates.COLUMNS.value)
                coord2 = random.choice(Coordinates.ROWS.value)
                msg = await thread.send(coord1 + coord2)
            else:
                msg = await self.bot.wait_for('message', check = lambda msg: msg.author.id == players[turn].id and msg.channel == thread)
            
            coords = self.convert_a1_coords_to_indeces(msg.content.upper())
            if not coords:
                await thread.send('```Координаты должны быть в формате "А1" (английские буквы)```', reference=msg)
                continue
            
            err = fields[turn].attack((coords[0], coords[1]))
            
            if err == -2:
                await thread.send('я очень надеюсь что до этой ошибки дело не дойдёт потому что я понятия не имею как это может произойти типа координаты правильные корабль найден но у него нет этой ячейки???', reference=msg)
                continue
            
            if err == -1:
                await thread.send('Эта ячейка уже была атакована!', reference=msg)
                continue
            
            swap_turn = False
            if err == 0:
                await thread.send('Промах', reference=msg)
                swap_turn = True
            elif err == 1:
                await thread.send('💥 Попадание! 💥', reference=msg)
            elif err == 2:
                await thread.send(f'💀 Попадание! Корабль уничтожен! 💀\nУ противника остаётся {fields[turn].alive_ships_count()} корабль(-ей)', reference=msg)
            
            await field_messages[turn].edit(attachments=[fields[turn].build_image()])
            
            if fields[turn].alive_ships_count() <= 0:
                await thread.send(f'Игрок <@{players[turn].id}> уничтожил все корабли соперника и забирает победу!', reference=msg)
                await field_messages[0].edit(attachments=[fields[0].build_image(show_ships=True)])
                await field_messages[1].edit(attachments=[fields[1].build_image(show_ships=True)])
                break
            
            if swap_turn:
                turn = 1 - turn
            
    def convert_a1_coords_to_indeces(self, a1: str):
        if len(a1) != 2 and len(a1) != 3:
            return False
        
        if len(a1) == 2:
            a1_arr = list(a1)
        elif len(a1) == 3:
            a1_arr = [a1[0], a1[1]+a1[2]]
        indeces_arr = [-1, -1]
        
        try:
            indeces_arr[0] = Coordinates.ROWS.value.index(a1_arr[1])
            indeces_arr[1] = Coordinates.COLUMNS.value.index(a1_arr[0])
        except ValueError:
            return False
        
        return indeces_arr
        
    async def place_ships(self, user: discord.Member):
        if user.id == self.bot.user.id:
            field = Field(10, 10)
            field.generate()
            return field
            
        dm_channel = await user.create_dm()
        
        dm_embed = discord.Embed(title='Размещение кораблей', color=discord.Color.blue())
        dm_embed_msg = 'Скопируйте сообщение из блока ниже, вставьте его в текстовое поле и замените ▯ на ▮ (или любой другой символ) в тех местах, где хотите поставить корабль.\n'
        dm_embed_msg += '\nВам надо поставить: \n'
        dm_embed_msg += '* 1 корабль длиной в 4 клетки\n'
        dm_embed_msg += '* 2 корабля длиной в 3 клетки\n'
        dm_embed_msg += '* 3 корабля длиной в 2 клетки\n'
        dm_embed_msg += '* 4 корабля длиной в 1 клетку\n'
        dm_embed_msg += 'Корабли не могут соприкасаться сторонами и углами.\n'
        dm_embed_msg += '\n```\n'
        dm_embed_msg += "▯▯▯▯▯▯▯▯▯▯\n" * 10
        dm_embed_msg += '```'
        dm_embed_msg += '\nИли напишите "рандом" для случайной генерации поля.'
        
        dm_embed.description = dm_embed_msg
        dm_embed.set_footer(text='Для подтверждения выбора последнего поля в этом диалоге напишите "да"')
        
        await dm_channel.send(embed=dm_embed)
        
        def check(msg):
            return isinstance(msg.channel, discord.channel.DMChannel) and msg.author.id == user.id
        
        accepted = False
        field_obj = None
        while not accepted:
            msg = await self.bot.wait_for('message', check=check)
                        
            if msg.content != 'рандом' and msg.content != 'да':
                field = list(map(list, msg.content.replace(' ', '').split('\n')))
                
                if len(field) != 10 or False in list(map(lambda x: len(x) == 10, field)):
                    await dm_channel.send(reference=msg, content='Поле должно быть размером 10x10 символов (пробелы игнорируются)')
                    continue
                
                replace = lambda x: 0 if x == '▯' else 1
                field = [list(map(replace, x)) for x in field]
                
                found_ships = {1: [], 2: [], 3: [], 4: []}
                
                field_copy = field.copy()
                i = 0
                j = 0
                error = False
                for i in range(len(field_copy)):
                    for j in range(len(field_copy[0])):
                        if field_copy[i][j] == 1:
                            i_inc = 0
                            j_inc = 0
                            if i+1 < len(field_copy) and field_copy[i+1][j] == 1:
                                i_inc = 1
                            elif j+1 < len(field_copy[0]) and field_copy[i][j+1] == 1:
                                j_inc = 1
                            
                            if i_inc == 0 and j_inc == 0:
                                ship_size = 1
                            else:                            
                                ship_size = 0
                                i_ = i
                                j_ = j
                                while field_copy[i_][j_] == 1:
                                    ship_size += 1
                                    
                                    if i_ + i_inc < len(field_copy):
                                        i_ += i_inc
                                    else: break
                                    if j_ + j_inc < len(field_copy[0]):
                                        j_ += j_inc
                                    else: break
                            
                            field_copy[i][j] = 0
                            for k in range(ship_size):
                                field_copy[i+i_inc*k][j+j_inc*k] = 0
                            
                            '''
                            for k in range(len(field_copy)):
                                print(field_copy[k])
                            print('--------------------')
                            '''

                            if not ship_size in found_ships.keys():
                                error = True
                                await dm_channel.send(reference=msg, content=f'Корабль не может быть длиной в {ship_size} клеток')
                                break
                            
                            if i_inc == 1:
                                orientation = Orientation.VERTICAL
                            else:
                                orientation = Orientation.HORIZONTAL
                            found_ships[ship_size].append(Ship((i, j), ship_size, orientation))
                                    
                        if error: break
                    if error: break
                
                if error:
                    continue        
                
                if len(found_ships[1]) != 4 or len(found_ships[2]) != 3 or len(found_ships[3]) != 2 or len(found_ships[4]) != 1:
                    await dm_channel.send(reference=msg, content=f'Неверное количество кораблей')
                    continue
                
                field_obj = Field(10, 10)
                field_obj.ships = found_ships
                if not field_obj.is_valid():
                    await dm_channel.send(reference=msg, content=f'Корабли не могут соприкасаться сторонами и углами')
                    continue
                
                await msg.add_reaction('✅')
                await dm_channel.send(reference=msg, content=f'Поле принято, напишите "да" для подтверждения', file=field_obj.build_image(show_ships=True))
                
                field_obj = Field(10, 10)
                field_obj.ships = found_ships
            elif msg.content == 'рандом':
                field_obj = Field(10, 10)
                field_obj.generate()
                m = f'Случайная генерация поля...'
                m += '\nНапишите "да" для подтверждения (или своё поле, или ещё раз "рандом")'
                await dm_channel.send(reference=msg, content=m, file=field_obj.build_image(show_ships=True))
            elif msg.content == 'да':
                if not field_obj:
                    await dm_channel.send('нет блин нет')
                    continue
                
                if not field_obj.is_valid():
                    await dm_channel.send('На последнем поле неверно расставлены корабли')
                    continue
                
                accepted = True
                await dm_channel.send('Поле сохранено, ожидание соперника и начало игры')
                return field_obj
                
                
async def setup(bot):
    await bot.add_cog(Battleship(bot))