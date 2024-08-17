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
import base64

load_dotenv()

# Replace with your bot's token
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_HOST = os.getenv('API_HOST')
BOT_SECRET = os.getenv('BOT_SECRET')


# Replace with the target user's name
TARGET_USER = 'Hjerneskade(Meme Of The Day)'

# Replace with the specific guild name to operate in
#TARGET_GUILD_NAME = 'Beanhole™'

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
            message_age < timedelta(hours=72)
            and user != bot.user)

def should_react_to_message(message):
    return message.author.name == TARGET_USER

def search_filename(filename):
    pattern = r'^memeId_(?P<memeId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})_visualId_(?P<visualId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})_toptextId_(?P<toptextId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})_bottomtextId_(?P<bottomtextId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}).png$'

    match = re.search(pattern, filename)
    return match.group('memeId')

async def log_reaction(message, reaction, user):
    """Helper function to log reaction details."""
    emoji = reaction.emoji
    memeId = search_filename(message.attachments[0].filename)
    headers, data = prepare_vote_data(user, memeId, str(emoji)[0])
    await post_vote(bot.get_channel(reaction.message.channel.id), headers, data, False)

def react_to_message(message):
    for emoji in [f'{i}\N{COMBINING ENCLOSING KEYCAP}' for i in range(10)]:
        bot.loop.create_task(message.add_reaction(emoji))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
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

def format_json(json_string):
    try:
        return json.dumps(json.loads(json_string), indent=4)
    except json.JSONDecodeError as e:
        return f"Error decoding JSON: {e}"

@bot.tree.command(name="submit_meme", description="Submit a meme")
@app_commands.describe(visual_file="Upload the image", top_text="Top text of the meme (optional)", bottom_text="Bottom text of the meme (optional)", topics='Comma separated list of strings like so: ["Topic1","Topic2"]')
async def submit_meme(
    interaction: discord.Interaction,
    visual_file: discord.Attachment,
    top_text: str = None,
    bottom_text: str = None,
    topics: str = None
):
    try:
        await interaction.response.defer()

        file_bytes = await visual_file.read()
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
        
        response = requests.post(API_HOST + "Memes?renderMeme=true", data=data, files=files)
        
        if response.status_code == 201:
            file_bytes = io.BytesIO(base64.b64decode(response.json().get("renderedMeme")))
            file_bytes.seek(0)  

            await interaction.followup.send(content="Meme submitted to the database successfully!", file=discord.File(fp=file_bytes, filename="renderedMeme.png"))
        else:
            await interaction.followup.send("Failed to create meme. Status code: " + str(response.status_code))

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")


@bot.tree.command(name="render_meme", description="Render a meme without submitting it to the database")
@app_commands.describe(visual_file="Upload the image", top_text="Top text of the meme (optional)", bottom_text="Bottom text of the meme (optional)")
async def render_meme(
    interaction: discord.Interaction,
    visual_file: discord.Attachment,
    top_text: str = None,
    bottom_text: str = None,
):
    try:
        await interaction.response.defer()

        file_bytes = await visual_file.read()
        data = {
            "TopText": top_text,
            "BottomText": bottom_text,
            "FileName": visual_file.filename,
        }

        files = {
            "VisualFile": (visual_file.filename, file_bytes)
        }
        
        response = requests.get(API_HOST + "Memes/Render", data=data, files=files)
        
        if response.status_code == 200:
            file_bytes = io.BytesIO(response.content)
            file_bytes.seek(0)  

            await interaction.followup.send(content="Here is the rendered meme!", file=discord.File(fp=file_bytes, filename="renderedMeme.png"))
        else:
            await interaction.followup.send("Failed to render meme. Status code: " + str(response.status_code))

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")


@bot.tree.command(name='submit_memetext', description='Submit a meme text')
@app_commands.describe(text='The content to submit a meme with', position='The position in a meme, can be "toptext" or "bottomtext"', topics='Comma separated list of strings like so: ["Topic1","Topic2"]')
async def submit_memetext(interaction: discord.Interaction, text: str, position: str, topics: str = None):
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
        
        if response.status_code == 201:
            await interaction.followup.send("Memetext created successfully!\n" + "```json\n" + format_json(response.text) + "\n```")
        else:
            await interaction.followup.send("Failed to create meme. Status code: " + str(response.status_code))
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")


@bot.tree.command(name='delete_visual', description='Delete a MemeVisual)')
@app_commands.describe(id='The ID of the element to be deleted.')
async def delete_visual(interaction: discord.Interaction, id: str):
    await interaction.response.defer()
    await delete_element(interaction, id, "visuals/")

@bot.tree.command(name='delete_text', description='Delete a MemeText)')
@app_commands.describe(id='The ID of the element to be deleted.')
async def delete_text(interaction: discord.Interaction, id: str):
    await interaction.response.defer()
    await delete_element(interaction, id, "texts/")

@bot.tree.command(name='delete_meme', description='Delete a Meme)')
@app_commands.describe(id='The ID of the element to be deleted.')
async def delete_meme(interaction: discord.Interaction, id: str):
    await interaction.response.defer()
    await delete_element(interaction, id, "memes/")

async def delete_element(interaction, id, endpoint):
    try:
        print("user id:", interaction.user.id)
        if(interaction.user.id != 319532244463255552):
            return await interaction.followup.send("You are not allowed, need more dubloons")
        response = requests.delete(API_HOST + endpoint + id)
        
        if response.status_code == 204:
            await interaction.followup.send("Element deleted successfully!")
        else:
            await interaction.followup.send("Failed to deleted element. Status code: " + str(response.status_code))
    except Exception as e:
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
    
        if response.status_code == 201 or response.status_code == 200:
            if should_post_success:
                await followup.send("Vote successful!\n" + "```json\n" + format_json(response.text) + "\n```")
        else:
            await followup.send("Failed to vote. Status code: " + str(response.status_code))
    except Exception as e:
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


@bot.tree.command(name="submit_memevisual", description="Submit a meme")
@app_commands.describe(file="Upload the image", topics='Comma separated list of strings like so: ["Topic1","Topic2"]')
async def submit_memevisual(
    interaction: discord.Interaction,
    file: discord.Attachment,
    topics: str = None
):
    try:
        await interaction.response.defer()

        file_bytes = await file.read()
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
        
        response = requests.post(API_HOST + "Visuals", data=data, files=files)
        
        if response.status_code == 201:
            await interaction.followup.send("MemeVisual created successfully!\n" + "```json\n" + format_json(response.text) + "\n```")
        else:
            await interaction.followup.send("Failed to create MemeVisual. Status code: " + str(response.status_code))

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")


@bot.tree.command(name="dubloons", description="Get the sum of your dubloons")
@app_commands.describe()
async def dubloons(
    interaction: discord.Interaction
):
    try:
        await interaction.response.defer()
        print(interaction.user.id)
        response = requests.get(API_HOST + f"users/{interaction.user.id}/Dubloons")
        
        if response.status_code == 200:
            await interaction.followup.send(f"You have {int(float(response.content.decode()))} dubloons!", ephemeral=True)
        else:
            await interaction.followup.send("Failed to fetch dubloons. Status code: " + str(response.status_code))

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")

bot.run(TOKEN)