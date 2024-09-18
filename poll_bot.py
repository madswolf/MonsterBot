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
IS_DEVELOPMENT = os.getenv('BOT_SECRET')

# Replace with the target user's name
TARGET_USER = 'Hjerneskade(Meme Of The Day)'

# Replace with the specific guild name to operate in
#TARGET_GUILD_NAME = 'Beanhole™'

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def defer_ephemeral(interaction):
    await interaction.response.defer(ephemeral=True)

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
        await defer_ephemeral(interaction)

        file_bytes = await visual_file.read()

        headers = {
            'ExternalUserId': str(interaction.user.id)
        }

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
        url = API_HOST +  ("Memes?renderMeme=true" if not IS_DEVELOPMENT else "Memes")
        response = requests.post(url, data=data, files=files, headers=headers)
        
        if response.status_code == 201:
            if(not IS_DEVELOPMENT):
                file_bytes = io.BytesIO(base64.b64decode(response.json().get("renderedMeme")))
                file_bytes.seek(0)  

                await interaction.followup.send(content="Meme submitted to the database successfully!", file=discord.File(fp=file_bytes, filename="renderedMeme.png"))
            else:
                await interaction.followup.send("Meme submitted to the database successfully!\n" + "```json\n" + format_json(response.text) + "\n```")
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
    await defer_ephemeral(interaction)
    if(position != "toptext" and position != "bottomtext"):
        await interaction.followup.send("Choose a position of either \"bottomtext\" or \"toptext\"")
        return

    headers = {
        'Content-Type': 'application/json',
        'ExternalUserId': str(interaction.user.id)
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

@bot.tree.command(name='submit_bottomtext', description='Submit a bottomtext')
@app_commands.describe(text='The content to submit', topics='Comma separated list of strings like so: ["Topic1","Topic2"]')
async def submit_memetext(interaction: discord.Interaction, text: str, topics: str = None):
    await defer_ephemeral(interaction)
    
    headers = {
        'Content-Type': 'application/json',
        'ExternalUserId': str(interaction.user.id)
    }
    data = {
        'text': text,
        'position': True,
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



@bot.tree.command(name='submit_toptext', description='Submit a meme toptext')
@app_commands.describe(text='The content to submit', topics='Comma separated list of strings like so: ["Topic1","Topic2"]')
async def submit_toptext(interaction: discord.Interaction, text: str, topics: str = None):
    await defer_ephemeral(interaction)
    headers = {
        'Content-Type': 'application/json',
        'ExternalUserId': str(interaction.user.id)
    }
    data = {
        'text': text,
        'position': False,
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
    await defer_ephemeral(interaction)
    await delete_element(interaction, id, "visuals/")

@bot.tree.command(name='delete_text', description='Delete a MemeText)')
@app_commands.describe(id='The ID of the element to be deleted.')
async def delete_text(interaction: discord.Interaction, id: str):
    await defer_ephemeral(interaction)
    await delete_element(interaction, id, "texts/")

@bot.tree.command(name='delete_meme', description='Delete a Meme)')
@app_commands.describe(id='The ID of the element to be deleted.')
async def delete_meme(interaction: discord.Interaction, id: str):
    await defer_ephemeral(interaction)
    await delete_element(interaction, id, "memes/")

async def delete_element(interaction, id, endpoint):
    try:
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
    await defer_ephemeral(interaction)
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

@bot.tree.command(name='transfer', description='Transfer dubloons from your account to another account')
@app_commands.describe(dublooncount='The number of dubloons that you want to tranfer(whole positive number)', user='The name of the user that you want to transfer to.')
async def vote(interaction: discord.Interaction, dublooncount: int, user: discord.user.User):
    await defer_ephemeral(interaction)
    if(dublooncount < 1):
        return await interaction.followup.send("The amount of dubloons to transfer must a positive number")

    if(interaction.user.id == user.id):
        return await interaction.followup.send("You cannot transfer dubloons to yourself, please provide another user")
    
    headers = {
        'Bot_Secret': BOT_SECRET,
        'ExternalUserId': str(interaction.user.id)
    }

    data = {
        "OtherUserId": user.id,
        "OtherUserName": user.name,
        "DubloonsToTransfer": dublooncount,
    }
    try:
        response = requests.post(API_HOST + "users/Transfer", headers=headers, data=data)
        if response.status_code == 200:
            if(user.id == bot.user.id):
                return await interaction.followup.send("Transfer successful! You have succesfully donated "+ str(dublooncount) + " to me... the bot")    
            await interaction.followup.send("Transfer successful! You have transferred " + str(dublooncount) + " to " + user.name)
        else:
            await interaction.followup.send("Failed to transfer. Status code: " + str(response.status_code) + " message: " + str(response.text))

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")


@bot.tree.command(name="submit_memevisual", description="Submit a meme")
@app_commands.describe(file="Upload the image", topics='Comma separated list of strings like so: ["Topic1","Topic2"]')
async def submit_memevisual(
    interaction: discord.Interaction,
    file: discord.Attachment,
    topics: str = None
):
    try:
        await defer_ephemeral(interaction)

        file_bytes = await file.read()
        headers = {
            'ExternalUserId': str(interaction.user.id)
        }
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
        
        response = requests.post(API_HOST + "Visuals", data=data, headers=headers, files=files)
        
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
        await defer_ephemeral(interaction)
        response = requests.get(API_HOST + f"users/{interaction.user.id}/Dubloons")

        if response.status_code == 200:
            await interaction.followup.send(f"You have {int(float(response.content.decode()))} dubloons!", ephemeral=True)
        else:
            await interaction.followup.send("Failed to fetch dubloons. Status code: " + str(response.status_code))

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")

@bot.tree.command(name="git_blame", description="Annotate who owns the abomination")
@app_commands.describe(meme_id="Id of the meme you want annotated")
async def git_blame(
    interaction: discord.Interaction,
    meme_id: str
):
    try:
        await defer_ephemeral(interaction)
        response = requests.get(API_HOST + f"memes/{meme_id}")

        if response.status_code == 200:
            message = f"These people are responsible for the abomination" + "```json\n" + format_json(json.dumps(extract_owners(response.text))) + "\n```"
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.followup.send("Failed to fetch dubloons. Status code: " + str(response.status_code))

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")


@bot.tree.context_menu(name='Git blame')
async def git_blame_menu(interaction: discord.Interaction, message: discord.Message):
    await defer_ephemeral(interaction)
    
    try:
        if message.attachments:
            meme_id = search_filename(message.attachments[0].filename)
            response = requests.get(API_HOST + f"memes/{meme_id}")
            if response.status_code == 200:
                
                message = f"These people are responsible for the abomination" + "```json\n" + format_json(json.dumps(extract_owners(response.text))) + "\n```"
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.followup.send("Failed to fetch dubloons. Status code: " + str(response.status_code))
        else:
            await interaction.response.send_message("No attachments found in the selected message.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")



def extract_owners(meme):
    meme = json.loads(meme)
    owners = {}
    
    owner = meme["memeVisual"]["owner"]["userName"] if meme["memeVisual"]["owner"] else "No one"
    id = meme["memeVisual"]["id"]
    owners["Visual"] = {"id":id, "owner":owner}

    if(meme["toptext"]):
        owner = meme["toptext"]["owner"]["userName"] if meme["toptext"]["owner"] else "No one"
        id = meme["toptext"]["id"]
        owners["Toptext"] = {"id":id, "owner":owner}

    if(meme["bottomText"]):
        owner = meme["bottomText"]["owner"]["userName"] if meme["bottomText"]["owner"] else "No one"
        id = meme["bottomText"]["id"]
        owners["Bottomtext"] = {"id":id, "owner":owner}

    return owners

bot.run(TOKEN)
