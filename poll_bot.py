import discord
from discord import app_commands
from discord.ext import commands
import requests
from PIL import Image, ImageEnhance
import io
import os
import time
import imageio
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import re

load_dotenv()

# Replace with your bot's token
TOKEN = os.getenv('DISCORD_BOT_TOKEN')


# Replace with the target user's name
TARGET_USER = 'Hjerneskade(Meme Of The Day)'

# Replace with the specific guild name to operate in
TARGET_GUILD_NAME = 'twlkawlkwa'

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store reactions with timestamps, user ID, and username
reactions_data = {}


def should_log_reaction(message, user):
    now = datetime.now(timezone.utc)
    message_age = now - message.created_at
    return (message.author.name == TARGET_USER and 
            message.guild.name == TARGET_GUILD_NAME and
            message_age < timedelta(hours=24)
            and user != bot.user)

def should_react_to_message(message):
    return message.author.name == TARGET_USER and message.guild.name == TARGET_GUILD_NAME

def search_filename(filename):
    pattern = r'^memeId_(?P<memeId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})_visualId_(?P<visualId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})_toptextId_(?P<toptextId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})_bottomtextId_(?P<bottomtextId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}).png$'

    match = re.search(pattern, filename)

    if match:
        memeId = match.group('memeId')
        visualId = match.group('visualId')
        toptextId = match.group('toptextId')
        bottomtextId = match.group('bottomtextId')

    print("memeId:", memeId, "visualId:", visualId, "toptextId:", toptextId, "bottomtextId:", bottomtextId)
    return (memeId, visualId, toptextId, bottomtextId)

def log_reaction(message, reaction, user):
    """Helper function to log reaction details."""
    emoji = reaction.emoji
    attachment_filename = message.attachments[0].filename

    reaction_info = {
        'timestamp': message.created_at.isoformat(),
        'user_id': user.id,
        'username': user.name,
        'reaction': emoji,
        'file_name': search_filename(attachment_filename)
    }
    if message.id not in reactions_data:
        reactions_data[message.id] = []
    reactions_data[message.id].append(reaction_info)
    print(f'Reaction added: {reaction_info}')

def react_to_message(message):
    for emoji in [f'{i}\N{COMBINING ENCLOSING KEYCAP}' for i in range(10)]:
        bot.loop.create_task(message.add_reaction(emoji))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    
    # Find the target guild by name
    target_guild = discord.utils.get(bot.guilds, name=TARGET_GUILD_NAME)
    
    if target_guild is None:
        print(f'Guild with name "{TARGET_GUILD_NAME}" not found.')
        return
    print(datetime.now())
    # Iterate over all channels in the target guild
    for channel in target_guild.text_channels:
        print(f'Loading recent messages from channel: {channel.name}')
        
        # Fetch recent messages from the channel
        async for message in channel.history(limit=100):  # Adjust limit as needed\
                if should_react_to_message(message):
                    react_to_message(message)

                # Store reactions if they exist
                for reaction in message.reactions:
                    async for user in reaction.users():
                        if should_log_reaction(message, user):
                            log_reaction(message, reaction, user)
    print(datetime.now())
    print("done looping")

@bot.event
async def on_message(message):
    if should_react_to_message(message):
        react_to_message(message)

@bot.event
async def on_reaction_add(reaction, user):
    message = reaction.message
    if should_log_reaction(message, user):
        log_reaction(message, reaction, user)

@bot.command(name='get_reactions')
async def get_reactions(ctx, message_id: int):
    # Fetch the reactions for a given message ID
    if message_id in reactions_data:
        await ctx.send(f'Reactions for message {message_id}: {reactions_data[message_id]}')
    else:
        await ctx.send('No reactions recorded for this message ID.')

bot.run(TOKEN)