import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import random
import asyncio
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.on_cooldown = set()
        self.levels_data = {}
        self.load_data()
        self.level_boundaries = []
        self.calculate_level_boundaries()
        self.mpru_guild = self.bot.get_guild(1041059132448444509)
        self.bot_channel = self.mpru_guild.get_channel(1041066221413597276)
            
    group = app_commands.Group(name='levels', description='Команды связанные с системой уровней')
    
    @group.command(name='rank', description='Показывает ваш уровень на сервере')
    async def rank_command(self, interaction: discord.Interaction, user: discord.Member=None):
        await interaction.response.defer()
        
        if user:
            user_id = user.id
        else:
            user = interaction.user
            user_id = interaction.user.id
            
        xp = 0
        level = 0
        next_level_xp = 100
        
        user_data = self.levels_data.get(str(user_id))
        if user_data:
            level = user_data['level']
            if level > 0:
                xp = user_data['xp'] - self.level_boundaries[level-1]
            else:
                xp = user_data['xp']
            next_level_xp = self.level_boundaries[level]
        else:
            return
        
        rank = 0
        img = await self.generate_rank_image(interaction.guild.get_member(user.id), rank, level, xp)
        
        await interaction.followup.send(file=img)
    
    @group.command(name='setxp', description='Задать количество опыта пользователю')
    async def setxp_command(self, interaction: discord.Interaction, user: discord.Member, xp: int):
        if not self.is_admin(interaction):
            await interaction.response.send_message(f'А тебе низя :/', ephemeral=True)
            return
        
        if xp < 0:
            await interaction.response.send_message('Опыт не может быть отрицательным', ephemeral=True)
            return
        
        user_data = self.levels_data.get(str(user.id))
        if not user_data:
            user_data = self.register_user(user.id)
            
        user_data['xp'] = xp
        self.fix_level(user.id)
        self.save_data()
        
        await interaction.response.send_message('Успех', ephemeral=True)
    
    async def generate_rank_image(self, user, rank, level, xp):
        bg_color = (255, 255, 255, 255)
        image = Image.new('RGBA', (1066, 296), bg_color)
        transparent_color = (0, 0, 0, 0)
        card_bg_color = (10, 10, 10, 220)
        card_img = Image.new('RGBA', (1024*4, 256*4), transparent_color)
        imgDraw = ImageDraw.ImageDraw(card_img)
        imgDraw.rounded_rectangle((0, 0, 1024*4, 256*4), radius=40, fill=card_bg_color)
        card_img = card_img.resize((1024, 256), resample=Image.BILINEAR)
        imgDraw = ImageDraw.ImageDraw(card_img)
        
        # Avatar
        asset = user.display_avatar.with_size(256)
        data = BytesIO(await asset.read())
        imgAvatar = Image.open(data)
        avatarSize = (216, 216)
        avatarBigSize = (avatarSize[0]*3, avatarSize[1]*3)
        imgAvatar = imgAvatar.resize(avatarSize, resample=Image.BILINEAR)
        imgAvatar = self.remove_transparency(imgAvatar, (0, 0, 0))
        avatarMask = Image.new('L', avatarBigSize, 0)
        avatarMaskDraw = ImageDraw.Draw(avatarMask) 
        avatarMaskDraw.ellipse((0, 0) + avatarBigSize, fill=255)
        avatarMask = avatarMask.resize(avatarSize, resample=Image.BILINEAR)
        
        # Status
        color=(0, 0, 255, 0)
        status = str(user.status)
        if status == 'online':
            color = (59,165,92,255)
        elif status == 'offline':
            color = (116,127,141,255)
        elif status == 'idle':
            color = (250,166,26, 255)
        elif status == 'dnd':
            color = (237,66,69, 255)
        statusSize = (80, 80)
        bigSize = (statusSize[0]*3, statusSize[1]*3)
        imgStatus = Image.new('RGBA', bigSize, card_bg_color)
        imgStatusDraw = ImageDraw.Draw(imgStatus)
        imgStatusDraw.ellipse((36, 36)+(bigSize[0]-36, bigSize[1]-36), fill=color)
        imgStatus = imgStatus.resize(statusSize, resample=Image.BILINEAR)
        statusMask = Image.new('L', bigSize, 0)
        statusMaskDraw = ImageDraw.Draw(statusMask) 
        statusMaskDraw.ellipse((0, 0) + bigSize, fill=255)
        statusMask = statusMask.resize(statusSize, resample=Image.BILINEAR)
        
        # XP Bar
        if level > 0:
            xp_needed = self.level_boundaries[level] - self.level_boundaries[level-1]
        else:
            xp_needed = self.level_boundaries[level]
        
        full_width = 690
        filled_width = int(xp/xp_needed * full_width)  
        if filled_width < 48: filled_width = 48
        
        xpbar_height = 48
        xpbar_size = (full_width, xpbar_height)
        xpbar_bigsize = (xpbar_size[0]*3, xpbar_size[1]*3)
        xpbar_filled_size = (filled_width, xpbar_height)
        xpbar_filled_bigsize = (xpbar_filled_size[0]*3, xpbar_filled_size[1]*3)
        xpbar_img = Image.new('RGBA', xpbar_bigsize, card_bg_color)
        xpbar_draw = ImageDraw.Draw(xpbar_img)
        xpbar_draw.rounded_rectangle((0, 0) + (xpbar_bigsize[0]-1, xpbar_bigsize[1]-1), radius=xpbar_height*3-xpbar_height, fill=(100, 100, 100, 255))
        xpbar_draw.rounded_rectangle((0, 0) + (xpbar_filled_bigsize[0], xpbar_filled_bigsize[1]), radius=xpbar_height*3-xpbar_height, fill=(50, 255, 255, 255))
        xpbar_img = xpbar_img.resize(xpbar_size, resample=Image.BILINEAR)
        
        # Background
        bg_draw = ImageDraw.Draw(image)
        
        distance = int(image.width/4)
        circles = [[], []]
        for i in range(2):
            for j in range(4):
                circles[i].append((j*distance+100, i*distance))
                
        for row in circles:
            for circle in row:
                radius = random.randint(50, 250)
                r = random.randint(150, 255)
                g = random.randint(150, 255)
                b = random.randint(150, 255)
                pos = (circle[0]-radius, circle[1]-radius, circle[0]+radius, circle[1]+radius)
                bg_draw.ellipse(pos, fill=(r, g, b, 255))
        
        filter = ImageFilter.GaussianBlur(radius=30)
        image = image.filter(filter)
        
        # Text
        font_name = ImageFont.truetype('data/fonts/Geist-Black.otf', 48)
        font_xp = ImageFont.truetype('data/fonts/DroidSansMono.ttf', 40)
        font_rank_level_words = ImageFont.truetype('data/fonts/DroidSansMono.ttf', 40)
        font_rank_level = ImageFont.truetype('data/fonts/DroidSansMono.ttf', 80)
        
        xp_string = f'{self.convert_number_to_thousands(xp)}'
        xp_needed_string = f'/{self.convert_number_to_thousands(xp_needed)} XP'
        rank_string = f'RANK'
        level_string = f'LEVEL '
        
        imgDraw.text((324, 112), user.display_name, (255, 255, 255), font=font_name)
        
        imgDraw.text((1000, 166), xp_needed_string, (180, 180, 180, 255), anchor='rb', font=font_xp)
        left_x = 1000-font_xp.getmask(xp_needed_string).getbbox()[2]-2
        imgDraw.text((left_x, 166), xp_string, (255, 255, 255, 255), anchor='rb', font=font_xp)
        
        imgDraw.text((1000, 80), str(level), (50, 255, 255), anchor='rb', font=font_rank_level)
        left_x = 1000-font_rank_level.getmask(str(level)).getbbox()[2]+16
        imgDraw.text((left_x, 80), level_string, (50, 255, 255), anchor='rb', font=font_rank_level_words)
        left_x = left_x-font_rank_level_words.getmask(level_string).getbbox()[2]-40
        imgDraw.text((left_x, 80), '#'+str(rank), (255, 255, 255), anchor='rb', font=font_rank_level)
        left_x = left_x-font_rank_level.getmask('#'+str(rank)).getbbox()[2]-16
        imgDraw.text((left_x, 80), rank_string, (255, 255, 255), anchor='rb', font=font_rank_level_words)
        
        # Build final image
        card_img.paste(imgAvatar, (20, 20), mask=avatarMask)
        card_img.paste(imgStatus, (160, 160), mask=statusMask)
        card_img.paste(xpbar_img, (316, 180))
        
        image.paste(card_img, (20, 20), mask=card_img)
        
        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            return discord.File(fp=image_binary, filename='image.png')
    
    def remove_transparency(self, im, bg_colour=(255, 255, 255)):
        if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
            alpha = im.convert('RGBA').split()[-1]
            bg = Image.new("RGBA", im.size, bg_colour + (255,))
            bg.paste(im, mask=alpha)
            return bg

        else:
            return im
    
    def convert_number_to_thousands(self, num):
        if num < 1000: return str(num)
        
        return '{:.2f}K'.format(num/1000.0)
    
    def is_admin(self, interaction: discord.Interaction):
        for role in interaction.user.roles:
            if role.name == "Админ" or role.name == "Хелпер":
                return True
        return False
    
    async def give_xp(self, user_id):
        if user_id in self.on_cooldown:
            return
        self.on_cooldown.add(user_id)
        
        user_data = self.levels_data.get(str(user_id))
        if not user_data:
            user_data = self.register_user(user_id)
        
        random_value = random.randint(15, 25)
        user_data['xp'] += random_value
        self.save_data()
        
        if user_data['xp'] > self.level_boundaries[user_data['level']]:
            #await self.bot_channel.send(f'<@{user_id}>, ты только что получил {user_data["level"]+1} уровень!')
            user_data['level'] = user_data['level'] + 1
        self.save_data()
        
        await asyncio.sleep(60)
        self.on_cooldown.discard(user_id)
    
    def fix_level(self, user_id):
        user_data = self.levels_data.get(str(user_id))
        if not user_data:
            user_data = self.register_user(str(user_id))
        
        user_data['level'] = self.get_level_by_xp(user_data['xp'])

    def get_level_by_xp(self, xp):
        for i in range(len(self.level_boundaries)):
            if xp < self.level_boundaries[i]:
                return i
        return len(self.level_boundaries)-1
            
    def calculate_level_boundaries(self):
        self.level_boundaries = []
        total_xp = 0
        for i in range(101):
            total_xp += 5*i*i + i*50 + 100
            self.level_boundaries.append(total_xp)
                    
    def register_user(self, user_id):
        self.levels_data[user_id] = {'level': 0, 'xp': 0}
        return self.levels_data[user_id]
        
    def load_data(self):
        file = open('data/levels.json', 'r')     
        obj = file.read()
        self.levels_data = json.loads(obj)        
        file.close()

    def save_data(self):
        obj = json.dumps(self.levels_data, indent=4)
        file = open('data/levels.json', 'w')
        file.write(obj)
        file.close()    
    
async def setup(bot):
    await bot.add_cog(Levels(bot))