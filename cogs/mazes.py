from enum import Enum
from PIL import Image, ImageDraw
import random
import sys
import math
import discord
from discord.ext import commands
from discord import app_commands
from io import BytesIO
from timeit import default_timer as timer

sys.setrecursionlimit(10000)

class Walls(Enum):
    TOP = (-1, 0)
    RIGHT = (0, 1)
    BOTTOM = (1, 0)
    LEFT = (0, -1)

class Cell:
    def __init__(self, i: int, j: int, walls: set={Walls.TOP, Walls.RIGHT, Walls.BOTTOM, Walls.LEFT}):
        self.i = i
        self.j = j
        self.walls = walls
        self.visited = False
        self.finish = False

class Maze:
    def __init__(self, width: int, height: int, light_radius: float):
        if width < 0 or height < 0: return None
        
        self.width = width
        self.height = height
        self.light_radius = light_radius
        self.cells = [Cell(i, j, {Walls.TOP, Walls.RIGHT, Walls.BOTTOM, Walls.LEFT}) for i in range(width) for j in range(height)]
        self.max_distance = 0
        self.max_distance_cell = None
        self.player = None
    
    def move_player(self, direction):
        if direction in self.player.walls:
            return -1

        new_i = self.player.i + direction.value[0]
        new_j = self.player.j + direction.value[1]
        
        if new_i < 0 or new_j < 0 or new_i >= self.height or new_j >= self.width:
            return -1
        
        self.player = self.cells[new_i*self.width+new_j]
        return 0
    
    def player_on_finish(self):
        if self.player.finish:
            return True
        return False
    
    def generate_wilson(self):
        self.player = self.cells[0]
        
        starting_cell = self.cells[len(self.cells)//2 + self.width//2]
        maze = [starting_cell]
        
        not_maze = self.cells.copy()
        not_maze.remove(starting_cell)
                
        random_cell = random.choice(not_maze)
        path = [random_cell]
        count = 0
        while count <= 5000:
            count += 1
                        
            current_cell = path[len(path)-1]
            previous_cell = path[len(path)-2] if len(path) > 1 else None
            index = self.cells.index(current_cell)
            
            neighbours = []
            if current_cell.j - 1 >= 0:
                c = self.cells[index-1]
                if c != previous_cell:
                    neighbours.append(c)
            if current_cell.j + 1 < self.width:
                c = self.cells[index+1]
                if c != previous_cell:
                    neighbours.append(c)
            if current_cell.i - 1 >= 0:
                c = self.cells[index-self.width]
                if c != previous_cell:
                    neighbours.append(c)
            if current_cell.i + 1 < self.height:
                c = self.cells[index+self.width]
                if c != previous_cell:
                    neighbours.append(c)
            
            next_cell = random.choice(neighbours)
            
            if next_cell in path:
                ind = path.index(next_cell)
                for cell in path[ind:]:
                    path.remove(cell)

            next_cell.path = True
            path.append(next_cell)
                
            if next_cell in maze:
                for i in range(len(path)):
                    cell = path[i]
                    
                    maze.append(cell)
                    if cell in not_maze: not_maze.remove(cell)
                    
                    if i < len(path)-1:
                        next = path[i+1]
                        wall = (next.i - cell.i, next.j-cell.j)
                        if wall == Walls.TOP.value:
                            cell.walls.discard(Walls.TOP)
                            next.walls.discard(Walls.BOTTOM)
                        elif wall == Walls.RIGHT.value:
                            cell.walls.discard(Walls.RIGHT)
                            next.walls.discard(Walls.LEFT)
                        elif wall == Walls.BOTTOM.value:
                            cell.walls.discard(Walls.BOTTOM)
                            next.walls.discard(Walls.TOP)
                        elif wall == Walls.LEFT.value:
                            cell.walls.discard(Walls.LEFT)
                            next.walls.discard(Walls.RIGHT)
                        
                
                if len(not_maze) > 0:
                    path = [random.choice(not_maze)]
                else:
                    break
                
        i = random.randint(0, 1)*(self.height-1)
        j = random.randint(0, self.width-1)
        self.player = self.cells[i*self.width-1+j]
        
        while True:
            finish_i = random.randint(0, self.width-1)
            finish_j = random.randint(0, self.width-1)
            
            if math.sqrt((finish_i-i)**2 + (finish_j-j)**2) > self.width/2:
                break
                        
        self.cells[finish_i*self.width-1+finish_j].finish = True
    
    def generate_dfs(self, starting_cell: tuple):
        cell = self.cells[starting_cell[0]*self.width+starting_cell[1]]
        self.reset_visited()
        self.max_distance = 0
        self.player = cell
        self.dfs(cell, 1)
        self.max_distance_cell.finish = True
        
    def dfs(self, cell: Cell, d):
        cell.visited = True
        if d > self.max_distance:
            self.max_distance = d
            self.max_distance_cell = cell
        def get_unvisited_neighbours(cell: Cell) -> list:
            neighbours = []
            index = self.cells.index(cell)
            
            if cell.j - 1 >= 0:
                c = self.cells[index-1]
                if not c.visited:
                    neighbours.append(c)
            if cell.j + 1 < self.width:
                c = self.cells[index+1]
                if not c.visited:
                    neighbours.append(c)
            if cell.i - 1 >= 0:
                c = self.cells[index-self.width]
                if not c.visited:
                    neighbours.append(c)
            if cell.i + 1 < self.height:
                c = self.cells[index+self.width]
                if not c.visited:
                    neighbours.append(c)
                
            return neighbours
                
        neighbours = get_unvisited_neighbours(cell)
        random.shuffle(neighbours)
        
        while len(neighbours) > 0:
            neighbour = neighbours[0]

            if neighbour.visited: break
            
            wall = (neighbour.i - cell.i, neighbour.j-cell.j)
            if wall == Walls.TOP.value:
                cell.walls.discard(Walls.TOP)
                neighbour.walls.discard(Walls.BOTTOM)
            elif wall == Walls.RIGHT.value:
                cell.walls.discard(Walls.RIGHT)
                neighbour.walls.discard(Walls.LEFT)
            elif wall == Walls.BOTTOM.value:
                cell.walls.discard(Walls.BOTTOM)
                neighbour.walls.discard(Walls.TOP)
            elif wall == Walls.LEFT.value:
                cell.walls.discard(Walls.LEFT)
                neighbour.walls.discard(Walls.RIGHT)

            self.dfs(neighbour, d+1)
            neighbours.remove(neighbour)
                
    def reset_visited(self):
        for cell in self.cells:
            cell.visited = False            
    
    def build_image(self, lit=False) -> Image:
        size = (501, 501)
        
        cell_size = size[0]//self.width
        bg_color = (255, 255, 255, 255)
         
        image = Image.new('RGBA', size, bg_color)
        image_draw = ImageDraw.Draw(image)
        
        line_color = (0, 0, 0)
        line_width = 2
        
        for cell in self.cells:
            i = cell.i
            j = cell.j
            walls = cell.walls
            for wall in walls:
                if wall == Walls.TOP:
                    image_draw.line((j*cell_size, i*cell_size, (j+1)*cell_size, i*cell_size), line_color, line_width)
                elif wall == Walls.RIGHT:
                    image_draw.line(((j+1)*cell_size, i*cell_size, (j+1)*cell_size, (i+1)*cell_size), line_color, line_width)
                elif wall == Walls.BOTTOM:
                    image_draw.line((j*cell_size, (i+1)*cell_size, (j+1)*cell_size, (i+1)*cell_size), line_color, line_width)
                elif wall == Walls.LEFT:
                    image_draw.line((j*cell_size, i*cell_size, j*cell_size, (i+1)*cell_size), line_color, line_width)

            if cell.finish:
                image_draw.rectangle((j*cell_size+1, i*cell_size+1, (j+1)*cell_size-1, (i+1)*cell_size-1), (0, 255, 0))
        
        player_i = self.player.i
        player_j = self.player.j
        
        image_draw.ellipse((player_j*cell_size+5, player_i*cell_size+5, (player_j+1)*cell_size-5, (player_i+1)*cell_size-5), fill=(60, 60, 60, 255), outline=(0, 0, 0, 255), width=4)
        
        if not lit:
            player_x = int(self.player.j*cell_size+cell_size/2)
            player_y = int(self.player.i*cell_size+cell_size/2)
            light_distance = int(self.light_radius*cell_size)//2
            light_image = Image.new('RGBA', (size[0], size[1]), (0, 0, 0, 255))
            '''
            for y in range(max(0, player_y-light_distance), min(size[1], player_y+light_distance)):
                for x in range(max(0, player_x-light_distance), min(size[0], player_x+light_distance)):
                    distance = math.sqrt((x - player_x)**2 + (y-player_y)**2)

                    if distance > light_distance:
                        alpha = 255
                    else:
                        alpha = int(distance / light_distance * 255)
                    
                    light_image.putpixel((x, y), (0, 0, 0, alpha))
            '''            
            light_image_draw = ImageDraw.Draw(light_image)
            light_image_draw.ellipse((player_x-light_distance, player_y-light_distance, player_x+light_distance, player_y+light_distance), (0, 0, 0, 0))
            image.paste(light_image, (0, 0), light_image)
        
        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            return discord.File(fp=image_binary, filename='image.png')
    
class Mazes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.light_radius = 3.5
    
    @app_commands.command(name='maze', description='Сгенерировать лабиринт для прохождения')
    async def maze_command(self, interaction: discord.Interaction, size: int=10):
        if size < 3 or size > 30:
            await interaction.response.send_message('Размер лабиринта должен быть в пределах от 3 до 30', ephemeral=True)
            return
        
        maze = Maze(size, size, self.light_radius)
        maze.generate_wilson()
        
        view = MazeView(maze, interaction.user)
        
        await interaction.response.send_message(file=maze.build_image(), view=view)

class MazeView(discord.ui.View):
    def __init__(self, maze: Maze, user: discord.User):
        super().__init__()
        self.maze = maze
        self.user = user
        self.finished = False
    
    async def move(self, interaction: discord.Interaction, direction):
        if interaction.user != self.user:
            await interaction.response.send_message('Это не твой лабиринт! (Сгенерировать лабиринт можно командой /maze)', ephemeral=True)
            return
        
        if self.finished:
            await interaction.response.send_message('Этот лабиринт уже пройден', ephemeral=True)
            return
        self.maze.move_player(direction)
        if self.maze.player_on_finish():
            await interaction.response.edit_message(content='Ура ты победил!!! Ничего кроме этого сообщения ты не получишь потому что время позднее и я не хочу делать ещё что-то я последние часа три рисовал эти вонючие лабиринты отснань от меня', attachments=[self.maze.build_image(True)])
            self.finished = True
        else:
            file = self.maze.build_image()
            await interaction.response.edit_message(attachments=[file])
    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji.from_str('🟦'), row=0)
    async def align1_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('я существую просто ради выравнивания, не надо на меня нажимать 🥺', ephemeral=True)
    
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji.from_str('⬆️'), row=0)
    async def up_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move(interaction, Walls.TOP)
        
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji.from_str('🟦'), row=0)
    async def align2_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('я существую просто ради выравнивания, не надо на меня нажимать 🥺', ephemeral=True)
        
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji.from_str('⬅️'), row=1)
    async def left_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move(interaction, Walls.LEFT) 
        
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji.from_str('⬇️'), row=1)
    async def down_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move(interaction, Walls.BOTTOM)    
        
    @discord.ui.button(style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji.from_str('➡️'), row=1)
    async def right_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move(interaction, Walls.RIGHT)

async def setup(bot):
    await bot.add_cog(Mazes(bot))