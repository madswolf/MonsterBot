import discord
from discord import app_commands
from discord.ext import commands
import requests
from PIL import Image
import io
import os
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# Get the token from the .env file
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Function to open image from URL
def openImageFromUrl(url):
    response = requests.get(url)
    return Image.open(io.BytesIO(response.content))

# Define intents
intents = discord.Intents.default()
intents.message_content = True

# Set up the bot with intents
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands.')
    except Exception as e:
        print(f'Error syncing commands: {e}')

# Define the slash command
@bot.tree.command(name="post_image", description="Fetch and post an image from a specified URL.")
async def post_image(interaction: discord.Interaction):
    url = "http://192.168.1.66/capture"
    try:
        image = openImageFromUrl(url)
        with io.BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            await interaction.response.send_message(file=discord.File(fp=image_binary, filename='image.png'))
    except Exception as e:
        await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

# Run the bot with your token
bot.run(DISCORD_BOT_TOKEN)