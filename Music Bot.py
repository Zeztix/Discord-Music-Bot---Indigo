import discord
import json
from discord.ext import commands
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp as youtube_dl
import re
from flask import Flask
from threading import Thread
import asyncio

app = Flask('')

@app.route('/')
def home():
    return "200 OK", 200

def run():
    app.run(host='0.0.0.0', port=8080)

def start_server():
    server = Thread(target=run)
    server.start()

start_server()

intents = discord.Intents.all()
client = commands.Bot(command_prefix = '=', intents=intents, case_insensitive=True)

with open('config.json') as c:
   creds = json.load(c)
TOKEN = creds['discord_token']
SPOTIPY_CLIENT_ID = creds['spotify_id']
SPOTIPY_CLIENT_SECRET = creds['spotify_secret_id']

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))

# Set the maximum number of instances you want to allow
MAX_INSTANCES = 2 
current_instances = 0

@client.event
async def on_ready():
    global current_instances
    current_instances += 1

    if current_instances > MAX_INSTANCES - 1:
        print("Too many instances running. Closing the session.")
        await client.close()
    else:
        print(f"Bot is online. ({current_instances} instances running)")

    print('We have logged in as {0.user}'.format(client))
    print('Bot is ready!')
    activity = discord.Activity(name='Music | =play', type=discord.ActivityType.playing)
    await client.change_presence(activity=activity)

@client.event
async def on_disconnect():
    global current_instances
    current_instances -= 1
    print(f"Bot is offline. ({current_instances} instances running)")

@client.command(pass_context = True)
async def join(ctx):
    if ctx.voice_client is None and ctx.author.voice:
        channel = ctx.message.author.voice.channel
        await channel.connect()
    elif ctx.voice_client and ctx.author.voice:
        await ctx.send('I am already connected to the vc')
    else:
        await ctx.send('You are a not connected to the vc')

@client.command(pass_context = True)
async def leave(ctx):
    if ctx.voice_client and ctx.author.voice:
        await ctx.guild.voice_client.disconnect()
        await ctx.send('I disconnected from the vc')
    elif ctx.voice_client is None and ctx.author.voice:
        await ctx.send('I am not connected to the vc')
    else:
        await ctx.send('You are not connected to the vc')

song_queue = []
@client.command()
async def play(ctx, *, search_query):
    try:
        if search_query.startswith('http'):
            # Search for the YouTube URL
            youtube_url = f'ytsearch:{search_query}'
        else:
            # Search for the track on Spotify
            result = sp.search(q=search_query, type='track', limit=1)
            track = result['tracks']['items'][0]
            track_name = track['name']
            track_artist = track['artists'][0]['name']
            track_url = track['external_urls']['spotify']
            # Search for the YouTube URL
            youtube_url = f'ytsearch:{track_name} {track_artist}'

        song_queue.append(youtube_url)
            
        # Check if the bot is already in the voice channel, otherwise connect
        if ctx.voice_client != None and ctx.voice_client.is_connected():
            voice_client = ctx.voice_client
        elif ctx.voice_client == None:
            channel = ctx.author.voice.channel
            voice_client = await channel.connect()
        
        # Download and play the song from YouTube
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }
        YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'False'}
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            # Extract the info from the youtube URL
            info = ydl.extract_info(youtube_url, download=False)
            info['entries'][0]['url']
            if not voice_client.is_playing():
                await play_next_song(ctx, None)
            else:
                await ctx.send('Song queued')
    except Exception as e:
        print(e)
        await ctx.send('Something went wrong. Please try again later.')

async def play_next_song(ctx, error):
    if len(song_queue) > 0:
        next_song = song_queue.pop(0)
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }
        YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'False'}
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(next_song, download=False)
            url = info['entries'][0]['url']
            ctx.voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=lambda e: ctx.bot.loop.create_task(play_next_song(ctx, e)))
            
            # Separate the artist and the song name from each other and the rest
            split_title = re.split('-|\(', info['entries'][0]['title'])
            track_artist = split_title[0].strip()
            track_name = split_title[1].strip()

            # Search for the track on Spotify
            result = sp.search(q=f"{track_name} {track_artist}", type="track", limit=1)
            track = result["tracks"]["items"][0]
            track_url = track["external_urls"]["spotify"]

            await ctx.send(f'Now Playing: **{track_name}** by **{track_artist}** | {track_url}')
    if error:
        print(f"Error while playing song: {error}")

@client.command()
async def pause(ctx):
    # Checks if the user or the bot is vc, or if the bot is playing music
    server = ctx.message.guild
    voice_channel = server.voice_client
    if ctx.voice_client is not None and ctx.voice_client.is_playing() and ctx.author.voice is not None:
        voice_channel.pause()
        await ctx.send('Music paused')
    elif ctx.voice_client is not None and ctx.author.voice is not None:
        await ctx.send('There is no music playing currently')
    elif ctx.voice_client is None and ctx.author.voice is not None:
        await ctx.send('I am not connected to a vc')
    else:
        await ctx.send('You are not connected to the vc')

@client.command()
async def resume(ctx):
    # Check if music is paused and resume music
    server = ctx.message.guild
    voice_channel = server.voice_client
    if ctx.voice_client is not None and ctx.voice_client.is_paused() and ctx.author.voice is not None:
        voice_channel.resume()
        await ctx.send('Resuming Music...')
    elif ctx.voice_client is not None and ctx.voice_client.is_playing() and ctx.author.voice is not None:
        await ctx.send('There is music playing currently')
    elif ctx.voice_client is None and ctx.author.voice is not None:
        await ctx.send('I am not connected to a vc')
    else:
        await ctx.send('You are not connected to the vc')
    

@client.command()
async def stop(ctx):
    # Check if music is playing and stop it
    server = ctx.message.guild
    voice_channel = server.voice_client
    if ctx.voice_client is not None and ctx.voice_client.is_playing() and ctx.author.voice is not None or ctx.voice_client is not None and ctx.voice_client.is_paused() and ctx.author.voice is not None:
        voice_channel.stop()
        await ctx.send('Music stopped')
    elif ctx.voice_client is not None and ctx.author.voice is not None:
        await ctx.send('There is no music playing or paused currently')
    elif ctx.voice_client is None and ctx.author.voice is not None:
        await ctx.send('I am not connected to a vc')
    else:
        await ctx.send('You are not connected to the vc')
    

@client.command()
async def skip(ctx, *, url2):
    # TODO fix this, it doensn't work
    try:
        # Check if the user wants to skip the current song
        url2[0] = url2[1]
        FFMPEG_OPTIONS = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn',
            }
        YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'False'}
        ctx.voice_client.play(discord.FFmpegPCMAudio(url2[1], **FFMPEG_OPTIONS))
    except Exception as e:
        print(e)
        await ctx.send("Couldn't skip song")

# TODO ADD LOOP COMMAND (loop the same song or playlist)

# TODO ADD A SONG COMMAND (to get song name and artist)

# TODO ADD A LAST (to play the last song played) -- not major


client.run(TOKEN)