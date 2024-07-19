import discord

class Emojis():
    def __init__(self, bot):
        self.bot = bot
        
        guild = bot.get_guild(1179406541384843404)
        if guild:
            self.emojis = guild.emojis
        
    def get_emoji_by_name(self, name: str):        
        for emoji in self.emojis:
            if emoji.name == name:
                return emoji
            
        return None