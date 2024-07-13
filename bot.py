import discord
from discord import app_commands
from discord.ext import commands
import requests
from PIL import Image
import io
import os
import time
import imageio
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

def openImageFromUrl(url):
    response = requests.get(url)
    return Image.open(io.BytesIO(response.content))

def captureStreamAsGif(url, duration=3, fps=10):
    frames = []
    try:
        stream = requests.get(url, stream=True, timeout=1)
        if stream.status_code == 404:
            return None
    except requests.RequestException as e:
        return None

    bytes_data = b''
    for chunk in stream.iter_content(chunk_size=1024):
        bytes_data += chunk
        a = bytes_data.find(b'\xff\xd8')
        b = bytes_data.find(b'\xff\xd9')

        if a != -1 and b != -1:
            jpg = bytes_data[a:b+2]
            bytes_data = bytes_data[b+2:]
            
            try:
                img = Image.open(io.BytesIO(jpg))
                img.verify()  # Verify the integrity of the image
                img = Image.open(io.BytesIO(jpg))  # Reload the image without verification
                frames.append(img)
            except Exception as e:
                continue

            if len(frames) >= fps * duration:
                break

    return frames

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands.')
    except Exception as e:
        print(f'Error syncing commands: {e}')

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

@bot.tree.command(name="post_gif", description="Capture a stream and post it as a GIF.")
async def post_gif(interaction: discord.Interaction):
    url = "http://192.168.1.66:81/stream"
    try:
        frames = captureStreamAsGif(url)
        if(frames is None):
           await interaction.response.send_message(f'The stream is busy or not available. Please try again.', ephemeral=True)
        gif_buffer = io.BytesIO()
        imageio.mimsave(gif_buffer, frames, format='GIF', fps=10, loop=0)
        gif_buffer.seek(0)
        await interaction.response.send_message(file=discord.File(fp=gif_buffer, filename='stream.gif'))
    except Exception as e:
        await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)

# Run the bot with your token
bot.run(DISCORD_BOT_TOKEN)