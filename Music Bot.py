import discord
import json
from discord.ext import commands
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp as youtube_dl
import re
from flask import Flask
from threading import Thread

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
client = commands.Bot(command_prefix = '=', intents=intents)

with open('config.json') as c:
   creds = json.load(c)
TOKEN = creds['discord_token']
SPOTIPY_CLIENT_ID = creds['spotify_id']
SPOTIPY_CLIENT_SECRET = creds['spotify_secret_id']

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET))

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    print('Bot is ready!')

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
        YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True'}

        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            # Extract the info from the youtube URL
            info = ydl.extract_info(youtube_url, download=False)
            
            url2 = info['entries'][0]['url']
            voice_client.play(discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS))
            # When a link is entered, it will reply with just the name and artist
            if search_query.startswith('http'):
                # Separate the artist and the song name from each other and the rest
                split_title = re.split('-|\(', info['entries'][0]['title'])
                track_artist = split_title[0].strip()
                track_name = split_title[1].strip()
                await ctx.send(f'Now Playing: **{track_name}** by **{track_artist}**')
            else:
                await ctx.send(f'Now Playing: **{track_name}** by **{track_artist}** | {track_url}')
    except Exception as e:
        print(e)
        await ctx.send('Something went wrong. Please try again later.')

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
    # TODO add if statement so if there is no music actually playing it will tell the user there is nothing to resume, otherwise resume music
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
    # TODO same thing here, if there is nothing to stop playing, then tell the user, otherwise stop the music
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
    

# TODO ADD LOOP COMMAND (loop the same song or playlist)

# TODO ADD A SONG COMMAND (to get song name and artist)

# TODO ADD A LAST (to play the last song played) -- not major


client.run(TOKEN)