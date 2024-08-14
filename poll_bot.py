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
import json

load_dotenv()

# Replace with your bot's token
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_HOST = os.getenv('API_HOST')
BOT_SECRET = os.getenv('BOT_SECRET')


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
    return match.group('memeId')

async def log_reaction(message, reaction, user):
    """Helper function to log reaction details."""
    emoji = reaction.emoji
    memeId = search_filename(message.attachments[0].filename)
    headers, data = prepare_vote_data(user, memeId, str(emoji)[0])
    print(memeId)
    print(data)
    await post_vote(bot.get_channel(reaction.message.channel.id), headers, data, True)

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
        async for message in channel.history(limit=1):  # Adjust limit as needed\
                if should_react_to_message(message):
                    react_to_message(message)

                # Store reactions if they exist
                for reaction in message.reactions:
                    async for user in reaction.users():
                        if should_log_reaction(message, user):
                            await log_reaction(message, reaction, user)
    print(datetime.now())
    print("done looping")
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands.')
    except Exception as e:
        print(f'Error syncing commands: {e}')

@bot.event
async def on_message(message):
    if should_react_to_message(message):
        react_to_message(message)

@bot.event
async def on_reaction_add(reaction, user):
    message = reaction.message
    if should_log_reaction(message, user):
        await log_reaction(message, reaction, user)

@bot.command(name='get_reactions')
async def get_reactions(ctx, message_id: int):
    # Fetch the reactions for a given message ID
    if message_id in reactions_data:
        await ctx.send(f'Reactions for message {message_id}: {reactions_data[message_id]}')
    else:
        await ctx.send('No reactions recorded for this message ID.')

# Define a new slash command to send "hello"
@bot.tree.command(name="hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("hello")

def format_json(json_string):
    try:
        # Parse the JSON string into a Python dictionary
        data = json.loads(json_string)
        
        # Convert the dictionary back to a JSON string with indentation
        formatted_json = json.dumps(data, indent=4)
        
        return formatted_json
    except json.JSONDecodeError as e:
        return f"Error decoding JSON: {e}"

@bot.tree.command(name="initiate", description="Initiate a command with an optional argument")
@app_commands.describe(option="The optional argument, can be 'all'")
async def initiate(interaction: discord.Interaction, option: str = None):
    commandname = "g4-sAB.GXC"
    if option == 'all':
        await interaction.response.send_message(f"`initiated {commandname} with option {option}.`")
    else:
        await interaction.response.send_message(f"`initiated {commandname}.`")

@bot.tree.command(name="create_meme", description="Create a meme")
@app_commands.describe(visual_file="Upload the image", top_text="Top text of the meme (optional)", bottom_text="Bottom text of the meme (optional)", topics='Comma separated list of strings like so: ["Topic1","Topic2"]')
async def create_meme(
    interaction: discord.Interaction,
    visual_file: discord.Attachment,
    top_text: str = None,
    bottom_text: str = None,
    topics: str = None
):
    try:
        # Acknowledge the interaction to prevent timeout
        await interaction.response.defer()

        # Download the attachment
        file_bytes = await visual_file.read()
        # Prepare the data and files for the request
        data = {
            "TopText": top_text,
            "BottomText": bottom_text,
            "FileName": visual_file.filename,
        }
        if(topics is not None):
            try:
                data["Topics"] = json.loads(topics)
            except Exception as e:
                return await interaction.followup.send(f"Topics is not in a valid format. Please enter the topics in a JSON list like so: [\"Topic\", \"Topic2\"]")
        files = {
            "VisualFile": (visual_file.filename, file_bytes)
        }
        
        # Make the request to the API
        response = requests.post(API_HOST + "Memes", data=data, files=files)
        
        # Send the result message
        if response.status_code == 201:
            await interaction.followup.send("Meme created successfully!\n" + "```json\n" + format_json(response.text) + "\n```")
        else:
            await interaction.followup.send("Failed to create meme. Status code: " + str(response.status_code))

    except Exception as e:
        # Handle exceptions and ensure a response is sent
        await interaction.followup.send(f"An error occurred: {str(e)}")


@bot.tree.command(name='create_memetext', description='Create a meme text')
@app_commands.describe(text='The content to create a meme with', position='The position in a meme, can be "toptext" or "bottomtext"', topics='Comma separated list of strings like so: ["Topic1","Topic2"]')
async def create_memetext(interaction: discord.Interaction, text: str, position: str, topics: str = None):
    await interaction.response.defer()
    if(position != "toptext" and position != "bottomtext"):
        await interaction.followup.send("Choose a position of either \"bottomtext\" or \"toptext\"")
        return

    headers = {
        'Content-Type': 'application/json'
    }
    
    data = {
        'text': text,
        'position': position == "bottomtext",
    }
    
    if(topics is not None):
        try:
            data["Topics"] = json.loads(topics)
        except Exception as e:
            return await interaction.followup.send(f"Topics is not in a valid format. Please enter the topics in a JSON list like so: [\"Topic\", \"Topic2\"]")
    
    try:
        response = requests.post(API_HOST + "texts", headers=headers, json=data)
        response.raise_for_status()  # Raise an error for bad status codes
        
        # Send the result message
        if response.status_code == 201:
            await interaction.followup.send("Memetext created successfully!\n" + "```json\n" + format_json(response.text) + "\n```")
        else:
            await interaction.followup.send("Failed to create meme. Status code: " + str(response.status_code))
    except Exception as e:
        # Handle exceptions and ensure a response is sent
        await interaction.followup.send(f"An error occurred: {str(e)}")


@bot.tree.command(name='delete_visual', description='Delete a MemeVisual)')
@app_commands.describe(id='The ID of the element to be deleted.')
async def delete_visual(interaction: discord.Interaction, id: str):
    await interaction.response.defer()
    await delete_element(interaction, id, "visuals/")

@bot.tree.command(name='delete_text', description='Delete a MemeText)')
@app_commands.describe(id='The ID of the element to be deleted.')
async def delete_visual(interaction: discord.Interaction, id: str):
    await interaction.response.defer()
    await delete_element(interaction, id, "texts/")

@bot.tree.command(name='delete_meme', description='Delete a Meme)')
@app_commands.describe(id='The ID of the element to be deleted.')
async def delete_visual(interaction: discord.Interaction, id: str):
    await interaction.response.defer()
    await delete_element(interaction, id, "memes/")

async def delete_element(interaction, id, endpoint):
    try:
        response = requests.delete(API_HOST + endpoint + id)
        response.raise_for_status()  # Raise an error for bad status codes
        
        # Send the result message
        if response.status_code == 204:
            await interaction.followup.send("Element deleted successfully!")
        else:
            await interaction.followup.send("Failed to deleted element. Status code: " + str(response.status_code))
    except Exception as e:
        # Handle exceptions and ensure a response is sent
        await interaction.followup.send(f"An error occurred: {str(e)}")

@bot.tree.command(name='vote', description='Vote on a votable(Meme, MemeVisual, MemeText)')
@app_commands.describe(elementid='The ID of the element to vote on.', votenumber='The number rating of the vote."')
async def vote(interaction: discord.Interaction, elementid: str, votenumber: int):
    await interaction.response.defer()
    if(votenumber < 0 or votenumber > 9):
        return await interaction.followup.send("VoteNumber Invalid value: VoteNumber can only be an integer from 0-9.")

    headers, data = prepare_vote_data(interaction.user, elementid, votenumber)
    
    await post_vote(interaction.followup, headers, data, True)

async def post_vote(followup, headers, data, should_post_success):
    try:
        response = requests.post(API_HOST + "votes", headers=headers, data=data)
        response.raise_for_status()  # Raise an error for bad status codes
    
        # Send the result message
        if response.status_code == 201 or response.status_code == 200:
            if should_post_success:
                await followup.send("Vote successful!\n" + "```json\n" + format_json(response.text) + "\n```")
        else:
            await followup.send("Failed to vote. Status code: " + str(response.status_code))
    except Exception as e:
        # Handle exceptions and ensure a response is sent
        await followup.send(f"An error occurred: {str(e)}")

def prepare_vote_data(user, elementid, votenumber):
    headers = {
        'Bot_Secret': BOT_SECRET
    }

    data = {
        'ElementIDs': [elementid],
        'VoteNumber': votenumber,
        'ExternalUserID': user.id,
        'ExternalUserName': user.name,
    }
    
    return headers,data


@bot.tree.command(name="create_memevisual", description="Create a meme")
@app_commands.describe(file="Upload the image", topics='Comma separated list of strings like so: ["Topic1","Topic2"]')
async def create_memevisual(
    interaction: discord.Interaction,
    file: discord.Attachment,
    topics: str = None
):
    try:
        # Acknowledge the interaction to prevent timeout
        await interaction.response.defer()

        # Download the attachment
        file_bytes = await file.read()
        
        # Prepare the data and files for the request
        data = {
        }
        if(topics is not None):
            try:
                data["Topics"] = json.loads(topics)
            except Exception as e:
                return await interaction.followup.send(f"Topics is not in a valid format. Please enter the topics in a JSON list like so: [\"Topic\", \"Topic2\"]")

        files = {
            "File": (file.filename, file_bytes)
        }
        
        # Make the request to the API
        response = requests.post(API_HOST + "Visuals", data=data, files=files)
        
        # Send the result message
        if response.status_code == 201:
            await interaction.followup.send("MemeVisual created successfully!\n" + "```json\n" + format_json(response.text) + "\n```")
        else:
            await interaction.followup.send("Failed to create MemeVisual. Status code: " + str(response.status_code))

    except Exception as e:
        # Handle exceptions and ensure a response is sent
        await interaction.followup.send(f"An error occurred: {str(e)}")

bot.run(TOKEN)