import discord
from discord.ext import commands
from discord import app_commands
import typing
from datetime import datetime, timezone
import asyncio
from random import random
import re

class Quotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def quote(self, ctx):
        oldest = 1669911960
        target = datetime.fromtimestamp(oldest + random() * (datetime.now(timezone.utc).timestamp() - oldest), tz=timezone.utc)

        tasks = []
        messages = []
        for channel in ctx.guild.channels:
            tasks.append(self.search_channel(ctx, channel, target, messages))
        await asyncio.gather(*tasks)

        messages = filter(self.quote_filter, messages)
        msg = min(messages, key=lambda x: abs(target - x.created_at))

        em = discord.Embed(description=msg.content, timestamp=msg.created_at, color=msg.author.color)
        em.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)

        if not msg.attachments:
            urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', msg.content)
            for url in urls:
                if any([ext in url for ext in ['.png', '.jpg', '.jpeg', '.gif']]):
                    em.set_image(url=url)
                    break
        elif 'image' in msg.attachments[0].content_type:
            em.set_image(url=msg.attachments[0].url)
        else:
            filename = msg.attachments[0].filename
            file_url = msg.attachments[0].url
            em.add_field(name="File", value=f"[{filename}]({file_url})")
            if not msg.content:
                em.description += f"\nThis message contains a file."


        em.description += f"\n\n[Jump to message]({msg.jump_url})"
        em.set_footer(text="#" + msg.channel.name)

        await ctx.send(embed=em)
    
    async def search_channel(self, ctx, channel, target, list):
        if not isinstance(channel, discord.TextChannel) or not channel.permissions_for(ctx.guild.me).read_message_history:
            return
        msg = [message async for message in channel.history(limit=3, around=target)]
        list.extend(msg)
    
    def quote_filter(self, msg):
        if msg.author.bot:
            return False
        if any([msg.content.lower().startswith(x) for x in ('m!', 'p!', '^', '$', '<@1135144510691758210>')]):
            return False
        if len(msg.content) == 1:
            if msg.content == '\'': # bacon
                return True
            return False
        return True
        
async def setup(bot):
    await bot.add_cog(Quotes(bot))