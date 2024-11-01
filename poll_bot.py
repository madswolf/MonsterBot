import math
import discord
from discord import app_commands
from discord.ext import commands
import requests
from PIL import Image, ImageChops
import io
import os
import time
import imageio
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import re
import json
import base64
from PIL.ExifTags import TAGS
import difflib

load_dotenv()

# Replace with your bot's token
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_HOST = os.getenv('API_HOST')
BOT_SECRET = os.getenv('BOT_SECRET')
IS_DEVELOPMENT = os.getenv('BOT_SECRET')
CURRENT_PLACEID = os.getenv('CURRENT_PLACEID')
CURRENT_TOPICID = os.getenv('CURRENT_TOPICID')
MEDIA_HOST = os.getenv('MEDIA_HOST')
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

def should_react_to_message(message):
    return message.author.name == TARGET_USER

def search_filename(filename):
    pattern = r'^memeId_(?P<memeId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})_visualId_(?P<visualId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})_toptextId_(?P<toptextId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})_bottomtextId_(?P<bottomtextId>[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}).png$'

    match = re.search(pattern, filename)
    return match.group('memeId')

def is_numeric_emoji(emoji):
    return emoji in [f'{i}\N{COMBINING ENCLOSING KEYCAP}' for i in range(10)]

def should_log_reaction(message, reaction, user):
    now = datetime.now(timezone.utc)
    message_age = now - message.created_at
    return (message.author.name == TARGET_USER and 
            message_age < timedelta(hours=72)
            and user != bot.user and is_numeric_emoji(reaction.emoji))

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
    if should_log_reaction(message, reaction, user):
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

@bot.tree.command(name='delete_votable', description='Delete a Votable (Meme, MemeVisual, MemeText)')
@app_commands.describe(id='The ID of the element to be deleted.')
@app_commands.describe(hard_delete='A boolean that determines if the element is deleted or removed from topic')
async def delete_votable(interaction: discord.Interaction, id: str, hard_delete: bool = False):
    await defer_ephemeral(interaction)
    await delete_element(interaction, id, "topics/votables/", hard_delete)

async def delete_element(interaction, id, endpoint, hard_delete = False):
    try:
        headers = {
            'Bot_Secret': BOT_SECRET,
            'ExternalUserId': str(interaction.user.id)
        }

        params = {
            'hardDelete': hard_delete
        }

        response = requests.delete(API_HOST + endpoint + id, headers=headers, params=params)
        
        if response.status_code == 200:
            await interaction.followup.send("Element deleted successfully!")
        else:
            await interaction.followup.send("Failed to delete element. Status code: " + str(response.status_code))
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

@bot.tree.command(name="mod_user", description="Mod a given user")
@app_commands.describe(user='The user that you want to mod.')
async def current_price_per_pixel(
    interaction: discord.Interaction,
    user: discord.user.User
):
    try:
        if(interaction.user.id != 319532244463255552):
            return await interaction.followup.send("You are not allowed, need more dubloons")
        await defer_ephemeral(interaction)

        headers = {
            'Bot_Secret': BOT_SECRET,
            'ExternalUserId': str(interaction.user.id)
        }

        response = requests.put(API_HOST + f"topics/{CURRENT_TOPICID}/mod/{user.id}", headers=headers)

        if response.status_code == 200:
            await interaction.followup.send("The user was sucessfully modded", ephemeral=True)
        else:
            await interaction.followup.send(f"Failed to mod user. Status code: {response.status_code}")

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
class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60.0)
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()

@bot.tree.command(name="submit_placesubmission", description="Submit a change to the current place(image)")
@app_commands.describe(file="The changed image that you would like to submit")
async def submit_placesubmission(
    interaction: discord.Interaction,
    file: discord.Attachment
):
    try:
        await defer_ephemeral(interaction)
        
        file_bytes = await file.read()
        if file.filename.endswith('.webp'):
            uploaded_image = Image.open(io.BytesIO(file_bytes))
            png_image_io = io.BytesIO()
            uploaded_image.save(png_image_io, format="PNG")
            png_image_io.seek(0)
            file_bytes = png_image_io.getvalue()
            file = discord.File(io.BytesIO(file_bytes), filename=file.filename.replace('.webp', '.png'))  # Overwrite file as PNG

        response = requests.get(MEDIA_HOST + f"places/{CURRENT_PLACEID}_latest.png")

        if response.status_code != 200:
            return await interaction.followup.send("Something went wrong in retrieving the current place. Please try again later.", ephemeral=True)

        reference_image = io.BytesIO(response.content)
        reference_image.seek(0)

        reference_image_render_timestamp = get_exif_comment(reference_image)
        reference_image.seek(0)

        if reference_image_render_timestamp is None:
            return await interaction.followup.send(content="The latest submission could not be read, please contact the developer to fix the problem.", ephemeral=True)

        reference_image_render_timestamp = reference_image_render_timestamp.strip().replace('\x00', '')

        if file.filename != f"{reference_image_render_timestamp}.png":
            return await interaction.followup.send(f"You have either based your changes off an older version of the current place or changed the name of the file. Please download the latest Place render and try again.", ephemeral=True)

        uploaded_image = Image.open(io.BytesIO(file_bytes))

        response = requests.get(API_HOST + f"MemePlaces/{CURRENT_PLACEID}/currentprice")

        current_price = float(json.loads(response.text)["pricePerPixel"])

        diff_pixels = count_pixel_changes(uploaded_image, Image.open(reference_image))
        if(diff_pixels == None):
            return await interaction.followup.send(f"The image you have submitted is not the same resolution as the current place image. Please download the latest place and try again.", ephemeral=True)

        if(diff_pixels == 0):
                return await interaction.followup.send(f"The image you have submitted has no changes (pixel diff of 0). Please download the latest place and try again.", ephemeral=True)
        
        required_funds = math.ceil(diff_pixels * current_price)

        response = requests.get(API_HOST + f"users/{interaction.user.id}/Dubloons")
        if response.status_code == 200:
            user_dubloons = int(float(response.content.decode()))
            if user_dubloons < required_funds:
                return await interaction.followup.send(f"You have {user_dubloons} dubloons, and you require {required_funds} dubloons to make this submission.", ephemeral=True)
        else:
            return await interaction.followup.send("Failed to fetch dubloons. Status code: " + str(response.status_code), ephemeral=True)
        view = ConfirmView()
        
        await interaction.followup.send(f"This submission will cost {required_funds}. Are you sure you want to proceed?", view=view)
        await view.wait()

        if view.value is None:
            return await interaction.followup.send("No response, submission cancelled.", ephemeral=True)
        elif view.value is False:
            return await interaction.followup.send("Submission cancelled.", ephemeral=True)
        else:
            await interaction.followup.send("Proceeding with submission. Please wait.", ephemeral=True)
        headers = {'ExternalUserId': str(interaction.user.id)}
        data = {"PlaceId": CURRENT_PLACEID}
        files = {"ImageWithChanges": (file.filename, file_bytes)}

        response = requests.post(API_HOST + f"MemePlaces/submissions/submit", data=data, headers=headers, files=files)

        if response.status_code == 200:
            return await interaction.followup.send("PlaceSubmission submitted successfully!\n" + "\n```json\n" + format_json(response.text) + "\n```", ephemeral=True)
        else:
            return await interaction.followup.send("Failed to submit PlaceSubmission. Status code: " + str(response.status_code), ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)


def count_pixel_changes(img1, img2):
    img1 = img1.convert('RGBA')
    img2 = img2.convert('RGBA')
    img1_height, img1_width = img1.size
    img2_height, img2_width = img2.size

    if(img1_height != img2_height or img1_width != img2_width):
        return None

    diff = ImageChops.difference(img1, img2)

    diff_pixels = sum(pixel != (0, 0, 0, 0) for pixel in diff.getdata())

    return diff_pixels


@bot.tree.command(name='delete_place_submission', description='Delete a place submission')
@app_commands.describe(id='The ID of the element to be deleted.')
async def delete_meme(interaction: discord.Interaction, id: str):
    await defer_ephemeral(interaction)
    if(interaction.user.id != 319532244463255552):
        return await interaction.followup.send("You are not allowed, need more dubloons")
    
    await delete_element(interaction, id, "MemePlaces/submissions/")


@bot.tree.command(name="current_price_per_pixel", description="Get the current price per pixel for the current place")
@app_commands.describe()
async def current_price_per_pixel(
    interaction: discord.Interaction,
):
    try:
        await defer_ephemeral(interaction)

        response = requests.get(API_HOST + f"MemePlaces/{CURRENT_PLACEID}/currentprice")

        if response.status_code == 200:
            await interaction.followup.send("The current price is \n" + "```json\n" + format_json(response.text) + "\n```", ephemeral=True)
        else:
            await interaction.followup.send(f"Failed to get the current price. Status code: {response.status_code}")

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")


@bot.tree.command(name="change_price_per_pixel", description="Change the current price per pixel for the current place.")
@app_commands.describe(new_price_per_pixel='The new price per pixel.')
async def change_price_per_pixel(
    interaction: discord.Interaction,
    new_price_per_pixel: float
):
    try:
        await defer_ephemeral(interaction)
        if(interaction.user.id != 319532244463255552):
            return await interaction.followup.send("You are not allowed to change the price")
        headers = {
            'Bot_Secret': BOT_SECRET
        }
        
        data = {
            'PlaceId': CURRENT_PLACEID,
            'NewPricePerPixel': new_price_per_pixel,
        }

        response = requests.post(API_HOST + f"MemePlaces/ChangePrice", data=data, headers=headers)

        if response.status_code == 200:
            await interaction.followup.send("The current place's price per pixel successfully changed! The new price is \n" + "```json\n" + format_json(response.text) + "\n```", ephemeral=True)
        else:
            await interaction.followup.send(f"Failed to change the current place's price per pixel. Status code: {response.status_code}")

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")

@bot.tree.command(name="rerender", description="Rerender the current place")
@app_commands.describe()
async def rerender(
    interaction: discord.Interaction,
):
    try:
        await defer_ephemeral(interaction)
        headers = {
            'Bot_Secret': BOT_SECRET
        }
        response = requests.post(API_HOST + f"MemePlaces/{CURRENT_PLACEID}/rerender", headers=headers)

        if response.status_code == 200:
            await interaction.followup.send(content="Place succesfully rerendered.")
        else:
            await interaction.followup.send(f"Failed to rerender image. Status code: {response.status_code}")

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")

@bot.tree.command(name="latest_place", description="Get the latest render of the place")
@app_commands.describe()
async def latest_place(
    interaction: discord.Interaction,
):
    try:
        await defer_ephemeral(interaction)
        response = requests.get(MEDIA_HOST + f"places/{CURRENT_PLACEID}_latest.png")

        if response.status_code == 200:
            file_bytes = io.BytesIO(response.content)
            file_bytes.seek(0)  

            timestamp = get_exif_comment(file_bytes)
            file_bytes.seek(0)
            
            if timestamp == None:
                return await interaction.followup.send(content="The latest submission could not be read, please contact the developer to fix the problem.")
            await interaction.followup.send(content="Here is the newest version!", file=discord.File(fp=file_bytes, filename=f"{timestamp}.png"))
        else:
            await interaction.followup.send("Failed to get the latest render of the place. Status code: " + str(response.status_code))

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")


def get_exif_comment(image_bytes):
    image = Image.open(image_bytes)

    exif_data = image._getexif()
    if not exif_data:
        return None

    for tag_id, value in exif_data.items():
        tag = TAGS.get(tag_id, tag_id)
        if tag == 'UserComment':
            if isinstance(value, bytes):
                decoded_comment = value.decode('utf-8', errors='ignore')
                if decoded_comment.startswith('UNICODE'):
                    return decoded_comment.replace('UNICODE', '').strip()
                return decoded_comment.strip()
            else:
                return str(value).strip().replace('\x00', '')

    return None

@bot.tree.command(name="dubloons", description="Get the sum of your dubloons")
@app_commands.describe()
async def dubloons(
    interaction: discord.Interaction,
      user: discord.user.User = None
):
    try:
        await defer_ephemeral(interaction)
        user_id = interaction.user.id
        if(user is not None):
            user_id = user.id
        response = requests.get(API_HOST + f"users/{user_id}/Dubloons")

        if response.status_code == 200:
            msg = f"You have {int(float(response.content.decode()))} dubloons!"
            if(user is not None):
                msg = f"{user.name} has {int(float(response.content.decode()))} dubloons!"
            await interaction.followup.send(msg, ephemeral=True)
        elif (response.status_code == 404):
            await interaction.followup.send("Given user has no Dubloons")
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
