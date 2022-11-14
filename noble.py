import discord
from discord.ext import commands
from discord import Option
import datetime
import aiosqlite
import random
import aiohttp
import os
import io
import asyncio
import requests
from easy_pil import *
from discord import File
import json
import re
from urllib.request import Request, urlopen
from discord.ext import tasks
import sqlite3
from PIL import ImageFont, ImageDraw, Image
from io import BytesIO
from discord import Message, Guild, TextChannel, Permissions
import time
import base64
from colorama import Fore
import wavelink
from wavelink.ext import spotify
from discord import ButtonStyle


with open('config.json','r', encoding='utf-8') as f:
  config = json.load(f)

prefix = config['prefix']
intents=discord.Intents.all()
bot = commands.Bot(command_prefix = prefix, intents=intents)
bot.remove_command("help")




#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━イベント━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#------Login info------\nログイン：{bot.user.name}({bot.user.id})\nバージョン：{discord.__version__}\n-----------------------

       

class TicketSettings(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(
        label="チケット作成", style=ButtonStyle.blurple, custom_id="create_ticket:blurple"
    )
    async def create_ticket(self, button : discord.ui.Button, interaction: discord.Interaction):
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
            interaction.user : discord.PermissionOverwrite(read_messages=True)

        }
        channel = await interaction.guild.create_text_channel(f"{interaction.user.name}-チケット",
        overwrites=overwrites)
        await interaction.response.send_message(f"チケットを作成できました {channel.mention}", ephemeral=True)
        embed = discord.Embed(title="チケット作成", description=f"{interaction.user.mention}がチケットを作成しました")
        await channel.send(embed=embed, view=TicketClose())

class TicketClose(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="チケットを閉じる", style=ButtonStyle.red, custom_id="ticket_settings:red"
    )
    async def close_ticket(self, button : discord.ui.Button, interaction: discord.Interaction):
        messages = await interaction.channel.history(limit=None, oldest_first=True).flatten()
        contents = [message.content for message in messages]
        final = ""
        for msg in contents:
            msg = msg + "\n"
            final = final + msg
        with open("transcript.txt", "w") as f:
            f.write(final)
        await interaction.response.send_message("チケットを閉じます", ephemeral=True)
        await interaction.channel.delete()
        await interaction.user.send("チケットを無事削除できました", file=discord.File(r"transcript.txt"))
        os.remove("transcript.txt")
    
    
  

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False

    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(TicketSettings())
            self.add_view(TicketClose())
            self.persistent_views_added = True



    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setticket(ctx, *, description=None):
        if description == None:
            embed = discord.Embed(title="サポート", description="ボタンをクリックするとチケットを作成できます\nチケットを作ったら問題を詳細に説明してください。そうすれば、管理者があなたに答えます")
            await ctx.send(embed=embed, view=TicketSettings())
        else:
            embed = discord.Embed(title="サポート", description=description)
            await ctx.send(embed=embed, view=TicketSettings())


class ControlPanel(discord.ui.View):
    def __init__(self, vc, ctx):
        super().__init__()
        self.vc = vc
        self.ctx = ctx
    
    @discord.ui.button(label="一時停止/再開", style=discord.ButtonStyle.green,emoji="⏯")
    async def resume_and_pause(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not interaction.user == self.ctx.author:
            return await interaction.response.send_message("そんなことはできません。 これらのボタンを使用するには、自分でコマンドを実行してください", ephemeral=True)
        for child in self.children:
            child.disabled = False
        if self.vc.is_paused():
            await self.vc.resume()
            button.style=discord.ButtonStyle.green
            await interaction.response.edit_message(content="再開しました", view=self)
        else:
            await self.vc.pause()
            button.style=discord.ButtonStyle.gray
            await interaction.response.edit_message(content="一時停止しました", view=self)

    @discord.ui.button(label="キュー", style=discord.ButtonStyle.blurple,emoji="🔄")
    async def queue(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not interaction.user == self.ctx.author:
            return await interaction.response.send_message("そんなことはできません。 これらのボタンを使用するには、自分でコマンドを実行してください", ephemeral=True)
        for child in self.children:
            child.disabled = False
        button.disabled = True
        if self.vc.queue.is_empty:
            return await interaction.response.send_message("キューは空です", ephemeral=True)
    
        em = discord.Embed(title="キュー")
        queue = self.vc.queue.copy()
        songCount = 0

        for song in queue:
            songCount += 1
            em.add_field(name=f"曲番号 {str(songCount)}", value=f"`{song}`")
        await interaction.response.edit_message(embed=em, view=self)
    
    @discord.ui.button(label="スキップ", style=discord.ButtonStyle.blurple,emoji="⏭")
    async def skip(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not interaction.user == self.ctx.author:
            return await interaction.response.send_message("そんなことはできません。 これらのボタンを使用するには、自分でコマンドを実行してください", ephemeral=True)
        for child in self.children:
            child.disabled = False
        button.disabled = True
        if self.vc.queue.is_empty:
            return await interaction.response.send_message("キューは空です", ephemeral=True)

        try:
            next_song = self.vc.queue.get()
            await self.vc.play(next_song)
            await interaction.response.edit_message(content=f"現在再生している曲 `{next_song}`", view=self)
        except Exception:
            return await interaction.response.send_message("キューは空です！", ephemeral=True)
    
    @discord.ui.button(label="離脱", style=discord.ButtonStyle.red,emoji="👋")
    async def disconnect(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not interaction.user == self.ctx.author:
            return await interaction.response.send_message("そんなことはできません。 これらのボタンを使用するには、自分でコマンドを実行してください", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await self.vc.disconnect()
        await interaction.response.edit_message(content="Botがボイスチャンネルから離脱しました", view=self)
        
    @discord.ui.button(label="ループ", style=discord.ButtonStyle.red,emoji="🔁")
    async def loop(self, button: discord.ui.Button, interaction: discord.Interaction):
        vc: wavelink.Player = self.ctx.voice_client
        if not interaction.user == self.ctx.author:
            return await interaction.response.send_message("そんなことはできません。 これらのボタンを使用するには、自分でコマンドを実行してください", ephemeral=True)
        for child in self.children:
            child.disabled = True
        try:
          vc.loop ^= True
        except:
            setattr(vc,"loop",False)
        if vc.loop:
         embed = discord.Embed(title="ループを設定しました",color=0xff0000)
         await interaction.response.send_message(embed=embed, ephemeral=True)
         return
        else:
         embed = discord.Embed(title="ループを解除しました",color=0xff0000)
         await interaction.response.send_message(embed=embed, ephemeral=True)

color = discord.Colour(int(config['color'],16))

async def node_connect():
  await bot.wait_until_ready()
  await wavelink.NodePool.create_node(
			bot=bot,
			host=config['lavalink']['host'],
			port=int(config['lavalink']['port']),
      password=config['lavalink']['password'],
		  https=config['lavalink']['https'],
      spotify_client=spotify.SpotifyClient(client_id="ef55488b6760421e808c793e5459bc06", client_secret="f2c9995b079443d598d00327c979a726")
    )

@bot.event
async def on_ready():
    print(Fore.BLUE + f"------Login info------\n[Bot]Botが起動しました\nBot:{bot.user}\nGuilds:{len(bot.guilds)}\nバージョン：{discord.__version__}\n-----------------------" + Fore.BLUE)
    print(Fore.GREEN + "------Node info------\n[Node]lavalinkのNodeに接続中です..." + Fore.RESET)
    setattr(bot, "db", await aiosqlite.connect("level.db"))
    bot.db = await aiosqlite.connect("warns.db")
    bot.db = await aiosqlite.connect("bank.db")
    await asyncio.sleep(3)
    async with bot.db.cursor() as cursor:
        await cursor.execute("CREATE TABLE IF NOT EXISTS warns(user INTEGER, reason TEXT, time INTEGER, guild INTEGER)")
        await cursor.execute("CREATE TABLE IF NOT EXISTS levels (level INTEGER, xp INTEGER, user INTEGER, guild INTEGER)")
        await cursor.execute("CREATE TABLE IF NOT EXISTS bank(wallet INTEGER, bank INTEGER, maxbank INTEGER, user INTEGER)")
        await cursor.execute("CREATE TABLE IF NOT EXISTS inv(laptop INTEGER, phone INTEGER, fakeid INTEGER, user INTEGER)")
        await cursor.execute("CREATE TABLE IF NOT EXISTS shop (name TEXT, id TEXT, desc TEXT, cost INTEGER)") 
    await bot.db.commit()
    print("データベース起動！")
    while True:
      try:
        bot.loop.create_task(node_connect())
        await wavelink.YouTubeTrack.search(query="test")
        print(Fore.GREEN + f"[Node]Nodeへの接続が完了しました\n-----------------------" + Fore.RESET)
        break
      except:
       await asyncio.sleep(10)
    CHANNEL_ID = 1037998685948227636
    channel = bot.get_channel(CHANNEL_ID)
    embed=discord.Embed(title="BOT起動", description="BOTを起動しました！", color=0x3683ff)
    embed.add_field(name="user",value=f"{len(bot.users)}",inline=True)
    embed.add_field(name="バージョン",value=f"{discord.__version__}",inline=True)
    embed.add_field(name="ping",value=f"{round(bot.latency *1000)}",inline=True)
    await channel.send(embed=embed)
    await bot.change_presence(activity = discord.Streaming(name = f".help | {len(bot.guilds)}サーバー | {len(bot.users)}ユーザー", url = "https://www.twitch.tv/dainy117"))

async def create_balance(user):
    async with bot.db.cursor() as cursor:
        await cursor.execute("INSERT INTO bank VALUES(?, ?, ?, ?)", (0, 100, 500, user.id))
    await bot.db.commit()
    return

async def create_inv(user):
    async with bot.db.cursor() as cursor:
        await cursor.execute("INSERT INTO inv VALUES(?, ?, ?, ?)", (0, 0, 0, user.id))
    await bot.db.commit()
    return

async def get_balance(user):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT wallet, bank, maxbank FROM bank WHERE user = ?", (user.id,))
        data = await cursor.fetchone()
        if data is None:
            await create_balance(user)
            return 0, 150, 500
        wallet, bank, maxbank = data[0], data[1], data[2]
        return wallet, bank, maxbank

async def get_inv(user):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT laptop, phone, fakeid FROM inv WHERE user = ?", (user.id,))
        data = await cursor.fetchone()
        if data is None:
            await create_inv(user)
            return 0, 0, 0
        laptop, phone, fakeid = data[0], data[1], data[2]
        return laptop, phone, fakeid

async def update_wallet(user, amount: int):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT wallet FROM bank WHERE user = ?", (user.id,))
        data = await cursor.fetchone()
        if data is None:
            await create_balance(user)
            return 0
        await cursor.execute("UPDATE bank SET wallet = ? WHERE user = ?", (data[0] + amount, user.id))
    await bot.db.commit()

async def update_bank(user, amount):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT wallet, bank, maxbank FROM bank WHERE user = ?", (user.id,))
        data = await cursor.fetchone()
        if data is None:
            await create_balance(user)
            return 0
        capacity = int(data[2] - data[1])
        if amount > capacity:
            await update_wallet(user, amount)
            return 1
        await cursor.execute("UPDATE bank SET bank = ? WHERE user = ?", (data[1] + amount, user.id))
    await bot.db.commit()

async def update_maxbank(user, amount):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT maxbank FROM bank WHERE user = ?", (user.id,))
        data = await cursor.fetchone()
        if data is None:
            await create_balance(user)
            return 0
        await cursor.execute("UPDATE bank SET maxbank = ? WHERE user = ?", (data[1] + amount, user.id))
    await bot.db.commit()

async def update_shop(name: str, id : str, desc: str, cost: int):
    async with bot.db.cursor() as cursor:
        await cursor.execute("INSERT INTO shop VALUES(?, ?, ?, ?)", (name, id, desc, cost))
        await bot.db.commit()
        return

async def addwarn(ctx, reason, user):
    async with bot.db.cursor() as cursor:
        await cursor.execute("INSERT INTO warns (user, reason, time, guild) VALUES (?, ?, ?, ?)", (user.id, reason, int(datetime.datetime.now().timestamp()), ctx.guild.id))
    await bot.db.commit()

@bot.command()
@commands.has_permissions(administrator=True)
async def warn(ctx, member: discord.Member, *, reason: str="理由がありません"):
    await addwarn(ctx, reason, member)
    embed = discord.Embed(title="メンバーを注意しました")
    embed.add_field(name="注意されたメンバー", value=f"{member.mention}")
    embed.add_field(name="理由", value=f"{reason}")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def removewarn(ctx, member: discord.Member):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT reason FROM warns WHERE user = ? AND guild = ?", (member.id, ctx.guild.id))
        data = await cursor.fetchone()
        if data:
            await cursor.execute("DELETE FROM warns WHERE user = ? AND guild = ?", (member.id, ctx.guild.id))
            await ctx.send("注意を削除した")
        else:
            await ctx.send("このメンバーは注意したことがありません")
    await bot.db.commit() 

@bot.command()
async def warns(ctx, member: discord.Member):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT reason, time FROM warns WHERE user = ? AND guild = ?", (member.id, ctx.guild.id))
        data = await cursor.fetchall()
        if data:
            em = discord.Embed(title=f"{member.name}の注意")
            warnnum = 0
            for table in data:
                warnnum += 1
                em.add_field(name=f"注意: {warnnum}", value=f"理由: {table[0]} | 注意された時間: <t:{int(table[1])}:F>")
            await ctx.send(embed=em)
        else:
            await ctx.send("メンバーは注意されていません")
    await bot.db.commit()    
    
@bot.command()
async def balance(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    wallet, bank, maxbank = await get_balance(member)
    em = discord.Embed(title=f"{member.name}の通貨")
    em.add_field(name="財布", value=wallet)
    em.add_field(name="銀行", value=f"{bank}/{maxbank}")
    await ctx.send(embed=em)

@bot.command()
async def beg(ctx):
    chances = random.randint(1, 4)
    if chances == 1:
        return await ctx.send("あなたは何も持っていません")
    amount = random.randint(5, 300)
    res = await update_wallet(ctx.author, amount)
    if res == 0:
        return await ctx.send("アカウントが見つからないため、アカウントが作成されています。コマンドを再実行してください")
    await ctx.send(f"{ctx.author.mention}のコイン: **{amount}**")


@bot.command()
async def withdraw(ctx, amount):
    wallet, bank, maxbank = await get_balance(ctx.author)
    try:
        amount = int(amount)
    except ValueError:
        pass
    if type(amount) == str:
        if amount.lower() == "max" or amount.lower() == "all":
            amount = int(bank)
    else:
        amount = int(amount)
    
    bank_res = await update_bank(ctx.author, -amount)
    wallet_res = await update_wallet(ctx.author, amount)
    if bank_res == 0 or wallet_res == 0:
        return await ctx.send("アカウントが見つからないため、アカウントが作成されています。コマンドを再実行してください")
    
    wallet, bank, maxbank = await get_balance(ctx.author)
    em = discord.Embed(title=f"{amount} コインが引き落とされました")
    em.add_field(name="新しい財布", value=wallet)
    em.add_field(name="新しい銀行", value=f"{bank}/{maxbank}")
    await ctx.send(embed=em)

@bot.command()
async def deposit(ctx, amount):
    wallet, bank, maxbank = await get_balance(ctx.author)
    try:
        amount = int(amount)
    except ValueError:
        pass
    if type(amount) == str:
        if amount.lower() == "max" or amount.lower() == "all":
            amount = int(wallet)
    else:
        amount = int(amount)
    
    bank_res = await update_bank(ctx.author, amount)
    wallet_res = await update_wallet(ctx.author, -amount)
    if bank_res == 0 or wallet_res == 0:
        return await ctx.send("アカウントが見つからないため、アカウントが作成されています。コマンドを再実行してください")
    elif bank_res == 1:
        return await ctx.send("銀行に十分な保管スペースがない")
    wallet, bank, maxbank = await get_balance(ctx.author)
    em = discord.Embed(title=f"{amount} コインが引き落とされました")
    em.add_field(name="新しい財布", value=wallet)
    em.add_field(name="新しい銀行", value=f"{bank}/{maxbank}")
    await ctx.send(embed=em)

@bot.command()
async def give(ctx, member: discord.Member, amount):
    wallet, bank, maxbank = await get_balance(ctx.author)
    try:
        amount = int(amount)
    except ValueError:
        pass
    if type(amount) == str:
        if amount.lower() == "max" or amount.lower() == "all":
            amount = int(wallet)
    else:
        amount = int(amount)
    
    wallet_res = await update_wallet(ctx.author, -amount)
    wallet_res2 = await update_wallet(member, amount)
    if wallet_res == 0 or wallet_res2 == 0:
        return await ctx.send("アカウントが見つからないため、アカウントが作成されています。コマンドを再実行してください")

    wallet2, bank2, maxbank2 = await get_balance(member)

    em = discord.Embed(title=f"{member.name} に {amount} コインを贈りました")
    em.add_field(name=f"{ctx.author.name}の財布", value=wallet)
    em.add_field(name=f"{member.name}の財布", value=wallet2)
    await ctx.send(embed=em) 


    
@bot.event
async def on_wavelink_track_end(player:wavelink.Player,track: wavelink.YouTubeTrack,reason):
  ctx = player.ctx
  vc: player = ctx.voice_client
  if vc.loop:
    await vc.play(track)
    return
  if vc.queue.is_empty:
    return
  next_song = vc.queue.get()
  await vc.play(next_song)
  embed=discord.Embed(title=next_song.title,url=next_song.uri,color=color)
  embed.set_author(name="曲を再生しました")
  embed.set_thumbnail(url=next_song.thumbnail)
  await ctx.send(embed=embed)



@tasks.loop(seconds=60)
async def loop():
    # botが起動するまで待つ
    await bot.wait_until_ready()
    await bot.change_presence(activity = discord.Streaming(name = f".help | {len(bot.guilds)}サーバー | {len(bot.users)}ユーザー", url = "https://www.twitch.tv/dainy117"))

loop.start()

@bot.command(aliases=["p"])
async def play(ctx, *, search=None):
  if not getattr(ctx.author.voice,"channel",None):
    embed = discord.Embed(title="ボイスチャンネルに参加してから使用してください",color=0xff0000)
    await ctx.send(embed=embed)
    return
  elif ctx.voice_client == None:
    vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
  if search == None:
    embed = discord.Embed(title="流したい曲名や、Youtubeの動画URLを送ってください",color=0xff0000)
    await ctx.send(embed=embed)
    return
  else:
    vc: wavelink.Player = ctx.voice_client
    if not re.search(r'https://\S+/watch\?v=\S+&list=\S+',search) == None:
      song = await wavelink.YouTubeTrack.search(query=search)
      playlist = True
    else:
      song = await wavelink.YouTubeTrack.search(query=search,return_first=True)
      playlist = False
    if vc.queue.is_empty and not vc.is_playing():
      if playlist == True:
        await vc.play(song.tracks[0])
        tracks = song.tracks
        song = tracks[0]
        tracks.pop(0)
        for track in tracks:
          await vc.queue.put_wait(track)
      if playlist == False:
        await vc.play(song)
      embed=discord.Embed(title=song.title,url=song.uri,color=color)
      embed.set_author(name="曲を再生しました")
      embed.add_field(name="アップローダー",value=f"`{song.author}`")
      embed.add_field(name="再生時間",value=f"`{str(datetime.timedelta(seconds=vc.track.length))}`")
      embed.set_image(url=f"{song.thumbnail}")
      view = ControlPanel(vc, ctx)
      await ctx.send(embed=embed, view=view)
      if playlist == True:
        embed = discord.Embed(title=f"プレイリストより{len(tracks)}曲を追加しました",color=0xff0000)
        await ctx.send(embed=embed)
    else:
      if playlist == True:
        tracks = song.tracks
        for track in tracks:
          await vc.queue.put_wait(track)
        embed = discord.Embed(title=f"プレイリストより{len(tracks)}曲を追加しました",color=0xff0000)
        await ctx.send(embed=embed)
      if playlist == False:
        await vc.queue.put_wait(song)
        embed=discord.Embed(title=song.title,url=song.uri,color=color)
        embed.set_author(name="曲を追加しました")
        embed.add_field(name="アップローダー",value=f"`{song.author}`")
        embed.set_thumbnail(url=f"{song.thumbnail}")
        await ctx.send(embed=embed)
    vc.ctx = ctx
    try:
      if vc.loop == True:
        return
    except Exception:
      setattr(vc,"loop",False)

@bot.command(aliases=["sp"])
async def spoplay(ctx, *, search: str):
    if not ctx.voice_client:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    elif not getattr(ctx.author.voice, "channel", None):
        embed = discord.Embed(title="まずはボイスチャンネルに参加してください",color=0xff0000)
        return await ctx.send(embed=embed)
    else:
        vc: wavelink.Player = ctx.voice_client
        
    if vc.queue.is_empty and not vc.is_playing():
        try:
            track = await spotify.SpotifyTrack.search(query=search, return_first=True)
            await vc.play(track)
            embed = discord.Embed(title=f"再生する曲 `{track.title}`",color=0xff0000)
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="Spotifyの**曲のURLを入力してください**。",color=0xff0000)
            await ctx.send(embed=embed)
            return print(e)
    else:
        await vc.queue.put_wait(search)
        embed = discord.Embed(title=f"`{search.title}` をキューに追加しました...",color=0xff0000)
        await ctx.send(embed=embed)
    vc.ctx = ctx
    try:
        if vc.loop: return
    except Exception:
        setattr(vc, "loop", False)

@bot.command()
async def search(ctx, *, search: str):
        try:
            tracks = await wavelink.YouTubeTrack.search(query=search)
        except:
            return await ctx.reply(embed=discord.Embed(title="この曲の検索中にエラーが発生しました", color=discord.Color.from_rgb(255, 255, 255)))

        if tracks is None:
            return await ctx.reply("曲が見つかりません")

        mbed = discord.Embed(
            title="曲を選択:",
            description=("\n".join(f"**{i+1}. {t.title}**" for i, t in enumerate(tracks[:5]))),
            color = discord.Color.from_rgb(255, 255, 255)
        )
        msg = await ctx.reply(embed=mbed)

        emojis_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '❌']
        emojis_dict = {
            "1️⃣": 0,
            "2️⃣": 1,
            "3️⃣": 2,
            "4️⃣": 3,
            "5️⃣": 4,
            "❌": -1
        }

        for emoji in list(emojis_list[:min(len(tracks), len(emojis_list))]):
            await msg.add_reaction(emoji)

        def check(res, user):
            return(res.emoji in emojis_list and user == ctx.author and res.message.id == msg.id)

        try:
            reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await msg.delete()
            return
        else:
            await msg.delete()

        node = wavelink.NodePool.get_node()
        vc = node.get_player(ctx.guild)

        try:
            if emojis_dict[reaction.emoji] == -1: return
            choosed_track = tracks[emojis_dict[reaction.emoji]]
        except:
            return

        vc: wavelink.Player = ctx.voice_client or await ctx.author.voice.channel.connect(cls=wavelink.Player)

        if not vc.is_playing() and not vc.is_paused():
            try:
                await vc.play(choosed_track)
                embed = discord.Embed(title=f"再生する曲 `{choosed_track.title}`",color=0xff0000)
                await ctx.send(embed=embed)
            except:
                return await ctx.reply(embed=discord.Embed(title="この曲の再生中にエラーが発生しました", color=discord.Color.from_rgb(255, 255, 255)))
        
        

        
        


@bot.command(aliases=["vcjoin"])
async def join(ctx):
  if not getattr(ctx.author.voice,"channel",None):
    embed = discord.Embed(title="ボイスチャンネルに参加してから使用してください",color=0xff0000)
    await ctx.send(embed=embed)
    return
  if ctx.voice_client == None:
    vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
  else:
    embed = discord.Embed(title="Botはすでに接続されています",color=0xff0000)
    await ctx.send(embed=embed)

@bot.command(aliases=["disconnect", "dc"])
async def leave(ctx):
  if ctx.voice_client == None:
    embed = discord.Embed(title="Botがボイスチャンネルに参加していません",color=0xff0000)
    await ctx.send(embed=embed)
    return
  elif not getattr(ctx.author.voice,"channel",None):
    embed = discord.Embed(title="ボイスチャンネルに参加してから使用してください",color=0xff0000)
    await ctx.send(embed=embed)
    return
  else:
    vc: wavelink.Player = ctx.voice_client
  await vc.disconnect()
  embed = discord.Embed(title="Botを切断しました",color=0xff0000)
  await ctx.send(embed=embed)



@bot.command(aliases=["pa"])
async def pause(ctx):
  if ctx.voice_client == None:
    embed = discord.Embed(title="Botがボイスチャンネルに参加していません",color=0xff0000)
    await ctx.send(embed=embed)
    return
  elif not getattr(ctx.author.voice,"channel",None):
    embed = discord.Embed(title="ボイスチャンネルに参加してから使用してください",color=0xff0000)
    await ctx.send(embed=embed)
    return
  else:
    vc: wavelink.Player = ctx.voice_client
    if vc.is_paused():
      embed = discord.Embed(title="曲はすでに一時停止されています",color=0xff0000)
      await ctx.send(embed=embed)
      return
    await vc.pause()
    embed = discord.Embed(title="音楽を一時停止しました",color=0xff0000)
    await ctx.send(embed=embed)

@bot.command(aliases=["re"])
async def resume(ctx):
  if ctx.voice_client == None:
    embed = discord.Embed(title="Botがボイスチャンネルに参加していません",color=0xff0000)
    await ctx.send(embed=embed)
    return
  elif not getattr(ctx.author.voice,"channel",None):
    embed = discord.Embed(title="ボイスチャンネルに参加してから使用してください",color=0xff0000)
    await ctx.send(embed=embed)
    return
  else:
    vc: wavelink.Player = ctx.voice_client
    if not vc.is_paused():
      embed = discord.Embed(title="音楽は一時停止されていません",color=0xff0000)
      await ctx.send(embed=embed)
      return
    await vc.resume()
    embed = discord.Embed(title="音楽の再生を再開しました",color=0xff0000)
    await ctx.send(embed=embed)

@bot.command(aliases=["next"])
async def skip(ctx):
  if ctx.voice_client == None:
    embed = discord.Embed(title="Botがボイスチャンネルに参加していません",color=0xff0000)
    await ctx.send(embed=embed)
    return
  elif not getattr(ctx.author.voice,"channel",None):
    embed = discord.Embed(title="ボイスチャンネルに参加してから使用してください",color=0xff0000)
    await ctx.send(embed=embed)
    return
  else:
    vc: wavelink.Player = ctx.voice_client
    if not vc.is_playing():
      embed = discord.Embed(title="音楽は再生されていません",color=0xff0000)
      await ctx.send(embed=embed)
      return
    if not vc.loop:
      if vc.queue.is_empty:
        embed = discord.Embed(title="キューに曲はありません",color=0xff0000)
        await ctx.send(embed=embed)
        return
    await vc.stop()
    embed = discord.Embed(title="スキップしました",color=0xff0000)
    await ctx.send(embed=embed)

@bot.command(aliases=["l"])
async def loop(ctx):
  if ctx.voice_client == None:
    embed = discord.Embed(title="Botがボイスチャンネルに参加していません",color=0xff0000)
    await ctx.send(embed=embed)
    return
  elif not getattr(ctx.author.voice,"channel",None):
    embed = discord.Embed(title="ボイスチャンネルに参加してから使用してください",color=0xff0000)
    await ctx.send(embed=embed)
    return
  vc: wavelink.Player = ctx.voice_client
  if not vc.is_playing():
    embed = discord.Embed(title="曲は再生されていません",color=0xff0000)
    await ctx.send(embed=embed)
    return
  try:
    vc.loop ^= True
  except:
    setattr(vc,"loop",False)
  if vc.loop:
    embed = discord.Embed(title="ループを設定しました",color=0xff0000)
    await ctx.send(embed=embed)
    return
  else:
    embed = discord.Embed(title="ループを解除しました",color=0xff0000)
    await ctx.send(embed=embed)
    return

@bot.command(aliases=["q"])
async def queue(ctx):
  if ctx.voice_client == None:
    embed = discord.Embed(title="Botがボイスチャンネルに参加していません",color=0xff0000)
    await ctx.send(embed=embed)
    return
  elif not getattr(ctx.author.voice,"channel",None):
    embed = discord.Embed(title="ボイスチャンネルに参加してから使用してください",color=0xff0000)
    await ctx.send(embed=embed)
    return
  vc: wavelink.Player = ctx.voice_client
  if vc.queue.is_empty:
    embed = discord.Embed(title="キューに曲はありません",color=0xff0000)
    await ctx.send(embed=embed)
    return
  queue = vc.queue.copy()
  songcount = 0
  embed=discord.Embed(title="キュー",color=color)
  for song in queue:
    songcount += 1
    embed.add_field(name=f"{songcount}曲目",value=f"[{song.title}]({song.uri})")
  await ctx.send(embed=embed)

@bot.command(aliases=["vol"])
async def volume(ctx, volume: int):
    if not ctx.voice_client:
        embed = discord.Embed(title="Botがボイスチャンネルに参加していないためボリュームを変更できません",color=0xff0000)
        return await ctx.send(embed=embed)
    elif not getattr(ctx.author.voice, "channel", None):
        embed = discord.Embed(title="まずはボイスチャンネルに参加してください",color=0xff0000)
        return await ctx.send(embed=embed)
    else:
        vc: wavelink.Player = ctx.voice_client
    if not vc.is_playing():
        embed = discord.Embed(title="まずは最初に音楽を再生してください",color=0xff0000)
        return await ctx.send(embed=embed)
    
    if volume > 100:
        embed = discord.Embed(title="ボリュームが高すぎます",color=0xff0000)
        return await ctx.send(embed=embed)
    elif volume < 0:
        embed = discord.Embed(title="ボリュームが低すぎます",color=0xff0000)
        return await ctx.send(embed=embed)
    embed = discord.Embed(title=f"ボリュームを '{volume}%' に設定します。",color=0xff0000)
    await ctx.send(embed=embed)    
    return await vc.set_volume(volume)

@bot.command(aliases=["np"])
async def nowplaying(ctx):
    if not ctx.voice_client:
        embed = discord.Embed(title="Botがボイスチャンネルに参加していないためボリュームを変更できません",color=0xff0000)
        return await ctx.send(embed=embed)
    elif not getattr(ctx.author.voice, "channel", None):
        embed = discord.Embed(title="まずはボイスチャンネルに参加してください",color=0xff0000)
        return await ctx.send(embed=embed)
    else:
        vc: wavelink.Player = ctx.voice_client
    
    if not vc.is_playing(): 
        embed = discord.Embed(title="まずは最初に音楽を再生してください",color=0xff0000)
        return await ctx.send(embed=embed)

    em = discord.Embed(title=f"現在再生している曲 {vc.track.title}", description=f"アーティスト: {vc.track.author}")
    em.add_field(name="再生時間", value=f"`{str(datetime.timedelta(seconds=vc.track.length))}`")
    em.add_field(name="エクストラ情報", value=f"曲のURL: [クリック]({str(vc.track.uri)})")
    return await ctx.send(embed=em)


if os.path.isfile("servers.json"):
    with open('servers.json', encoding='utf-8') as f:
        servers = json.load(f)
else:
    servers = {"servers": []}
    with open('servers.json', 'w') as f:
        json.dump(servers, f, indent=4)

@bot.command()
async def removeGlobal(ctx):
    if ctx.author.guild_permissions.administrator:
        if guild_exists(ctx.guild.id):
            globalid = get_globalChat_id(ctx.guild.id)
            if globalid != -1:
                servers["servers"].pop(globalid)
                with open('servers.json', 'w') as f:
                    json.dump(servers, f, indent=4)
            await ctx.send('Entfernt.')

@bot.command()
async def addGlobal(ctx):
    if ctx.author.guild_permissions.administrator:
        if not guild_exists(ctx.guild.id):
            server = {
                "guildid": ctx.guild.id,
                "channelid": ctx.channel.id,
                "invite": f'{(await ctx.channel.create_invite()).url}'
            }
            servers["servers"].append(server)
            with open('servers.json', 'w') as f:
                json.dump(servers, f, indent=4)
            embed = discord.Embed(title="**グローバルチャット**",
                                  description="サーバーの準備が整いました！"
                                              "これで、すべてのメッセージがこのチャンネルで送信され、"
                                              "このボットがサーバーにあるすべてのサーバーにリダイレクトします。",
                                  color=0x2ecc71)
            embed.set_footer(text="このサーバーには 5 秒かかることに注意してください"
                                  "スパムのためスローモードです！")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="あなたのサーバーには既に GlobalChat チャネルがあります。\r\n"
                                              "すべてのサーバーは、1 つの GlobalChat チャネルしか持つことができません。",
                                  color=0x2ecc71)
            await ctx.send(embed=embed)

#########################################

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not message.content.startswith(';'):
        if get_globalChat(message.guild.id, message.channel.id):
            await sendAll(message)
    await bot.process_commands(message)


#########################################

async def sendAll(message: Message):
    conent = message.content
    author = message.author
    attachments = message.attachments
    embed = discord.Embed(description=conent, color=author.color)

    icon = author.avatar.url
    embed.set_author(name=author.name, icon_url=icon)

    icon = message.guild.icon.url
    if icon:
        icon_url = icon
    embed.set_thumbnail(url=icon_url)
    embed.set_footer(text=f'Server: {message.guild.name}', icon_url=icon_url)

    links = '[botのウェブサイト](https://sites.google.com/view/ghanvbot/) ║ '
    globalchat = get_globalChat(message.guild.id, message.channel.id)
    if len(globalchat["invite"]) > 0:
        invite = globalchat["invite"]
        if 'discord.gg' not in invite:
            invite = 'https://discord.gg/{}'.format(invite)
        links += f'[メッセージサーバー]({invite})'

    embed.add_field(name='⠀', value='⠀', inline=False)
    embed.add_field(name='追加', value=links, inline=False)

        

    
    

    if len(attachments) > 0:
        img = attachments[0]
        embed.set_image(url=img.url)

    for server in servers["servers"]:
        guild: Guild = bot.get_guild(int(server["guildid"]))
        if guild:
            channel: TextChannel = guild.get_channel(int(server["channelid"]))
            if channel:
                perms: Permissions = channel.permissions_for(guild.get_member(bot.user.id))
                if perms.send_messages:
                    if perms.embed_links and perms.attach_files and perms.external_emojis:
                        await channel.send(embed=embed)
                    else:
                        await channel.send('{0}: {1}'.format(author.name, conent))
                        await channel.send('次の権限がありません: '
                                           '`メッセージの送信` `リンクの埋め込み` `ファイルの添付`'
                                           '`外部絵文字を使用`')
    await message.delete()


###############################

def guild_exists(guildid):
    for server in servers['servers']:
        if int(server['guildid'] == int(guildid)):
            return True
    return False


def get_globalChat(guild_id, channelid=None):
    globalChat = None
    for server in servers["servers"]:
        if int(server["guildid"]) == int(guild_id):
            if channelid:
                if int(server["channelid"]) == int(channelid):
                    globalChat = server
            else:
                globalChat = server
    return globalChat


def get_globalChat_id(guild_id):
    globalChat = -1
    i = 0
    for server in servers["servers"]:
        if int(server["guildid"]) == int(guild_id):
            globalChat = i
        i += 1
    return globalChat

@bot.event
async def on_guild_join(invite):
    for channel in invite.text_channels:
        if channel.permissions_for(invite.me).send_messages:
            em = discord.Embed(title="導入ありがとうございます",description="Botの初期prefixは`.`となっています\n不具合などございましたら`n!help`で確認していただくか**[サポートサーバー](https://discord.gg/Dgjv6R3quh)**までお願いします",color=0x2e5bff)
            await channel.send(embed=em)
        break


    
@bot.event
async def reply(message):
    reply = f'{message.author.mention}'
    embed = discord.Embed(title="Ghanv bot",description="このボットのprefixは`n!`です\n`n!help`を打つとコマンド一覧が表示されます\ncreate by dainy#4297")
    await message.channel.send(reply, embed=embed)

@bot.listen("on_message")
async def on_message(message):
    if bot.user in message.mentions:
        await reply(message)

class CustomButtons(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)

class Buttons(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

@bot.event
async def on_command_error(ctx, error):
    guild = ctx.message.guild
    cha = ctx.message.channel
    CHANNEL_ID = 1037998685948227636
    channel = bot.get_channel(CHANNEL_ID)
    embed = discord.Embed(title="Error", description=f"`{error}`", color=0x3683ff)
    embed.add_field(name="サーバー", value=ctx.guild.name, inline=True)
    embed.add_field(name="ユーザー", value=ctx.author.name, inline=True)
    await channel.send(embed=embed)
    view=Buttons()
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        view.add_item(discord.ui.Button(label="Error",style=discord.ButtonStyle.link,url=f"https://discord.com/channels/{guild.id}/{cha.id}/{ctx.message.id}"))
        embed = discord.Embed(title=":x: 失敗 -MissingPermissions", description="実行者の必要な権限が無いため実行出来ません。", timestamp=ctx.message.created_at, color=discord.Colour.red())
        embed.set_footer(text="お困りの場合は、サーバー管理者をメンションしてください。")
        await ctx.send(embed=embed, view=view)
    elif isinstance(error, discord.ext.commands.errors.BotMissingPermissions):
        view.add_item(discord.ui.Button(label="Error",style=discord.ButtonStyle.link,url=f"https://discord.com/channels/{guild.id}/{cha.id}/{ctx.message.id}"))
        embed = discord.Embed(title=":x: 失敗 -BotMissingPermissions", description="Botの必要な権限が無いため実行出来ません。", timestamp=ctx.message.created_at, color=discord.Colour.red())
        embed.set_footer(text="お困りの場合は、サーバー管理者をメンションしてください。")
        await ctx.send(embed=embed, view=view)
    elif isinstance(error, discord.ext.commands.errors.CommandNotFound):
        view.add_item(discord.ui.Button(label="Error",style=discord.ButtonStyle.link,url=f"https://discord.com/channels/{guild.id}/{cha.id}/{ctx.message.id}"))
        embed = discord.Embed(title=":x: 失敗 -CommandNotFound", description="不明なコマンドもしくは現在使用不可能なコマンドです。 `n!help`とうってコマンドを確認してください", timestamp=ctx.message.created_at, color=discord.Colour.red())
        embed.set_footer(text="お困りの場合は、サーバー管理者をメンションしてください。")
        await ctx.send(embed=embed, view=view)
    elif isinstance(error, discord.ext.commands.errors.MemberNotFound):
        view.add_item(discord.ui.Button(label="Error",style=discord.ButtonStyle.link,url=f"https://discord.com/channels/{guild.id}/{cha.id}/{ctx.message.id}"))
        embed = discord.Embed(title=":x: 失敗 -MemberNotFound", description="指定されたメンバーが見つかりません。", timestamp=ctx.message.created_at, color=discord.Colour.red())
        embed.set_footer(text="お困りの場合は、サーバー管理者をメンションしてください。")
        await ctx.send(embed=embed, view=view)
    elif isinstance(error, discord.ext.commands.errors.BadArgument):
        view.add_item(discord.ui.Button(label="Error",style=discord.ButtonStyle.link,url=f"https://discord.com/channels/{guild.id}/{cha.id}/{ctx.message.id}"))
        embed = discord.Embed(title=":x: 失敗 -BadArgument", description="指定された引数がエラーを起こしているため実行出来ません。", timestamp=ctx.message.created_at, color=discord.Colour.red())
        embed.set_footer(text="お困りの場合は、サーバー管理者をメンションしてください。")
        await ctx.send(embed=embed, view=view) 
    elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        view.add_item(discord.ui.Button(label="Error",style=discord.ButtonStyle.link,url=f"https://discord.com/channels/{guild.id}/{cha.id}/{ctx.message.id}"))
        embed = discord.Embed(title=":x: 失敗 -BadArgument", description="指定された引数が足りないため実行出来ません。", timestamp=ctx.message.created_at, color=discord.Colour.red())
        embed.set_footer(text="お困りの場合は、サーバー管理者をメンションしてください。")
        await ctx.send(embed=embed, view=view) 
    

class Select(discord.ui.Select):
    def __init__(self):
        options=[
            discord.SelectOption(label="ヘルプホーム",emoji="🏡",description="最初のヘルプホームに戻ります"),
            discord.SelectOption(label="情報",emoji="<:jyouhou:1025282238541213767>",description="情報コマンド一覧"),
            discord.SelectOption(label="管理者限定",emoji="<:kanrisya:1025283026520903720>",description="管理者限定コマンド一覧"),
            discord.SelectOption(label="面白い(笑)",emoji="<:omosiroi:1025284268223643698>",description="面白いコマンド一覧"),
            discord.SelectOption(label="検索",emoji="<:kennsaku:1025284285235744800>",description="検索コマンド一覧"),
            discord.SelectOption(label="フォートナイト",emoji="<:fortnite:1025271326790910004>",description="フォートナイトコマンド一覧"),
            discord.SelectOption(label="報告",emoji="<:houkoku:1025284996686155877>",description="報告コマンド一覧"),
            discord.SelectOption(label="音楽",emoji="<:ongaku:1025285006765068338>",description="音楽コマンド一覧"),
            discord.SelectOption(label="翻訳",emoji="<:Google_Translate_Icon:1026017077473058857>",description="翻訳コマンド一覧"),
            discord.SelectOption(label="天気",emoji="🌦",description="天気コマンド一覧"),
            discord.SelectOption(label="セッティング",emoji="⚙",description="セッティングコマンド一覧"),
            discord.SelectOption(label="グローバル",emoji="<:IQGroupGlobalicon:1033225964110495795>",description="グローバルコマンド一覧"),
            discord.SelectOption(label="通貨",emoji="💸",description="通貨コマンド一覧")
            ]
        super().__init__(placeholder="コマンドセレクト 🎞",max_values=1,min_values=1,options=options)
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "情報":
            embed = discord.Embed(title="情報 <:jyouhou:1025282238541213767>",description="`n!ping`\n`n!invite`\n`n!invites <@メンバー>`\n`n!avatar`\n`n!serverinfo`\n`n!userinfo`\n`n!url <調べたいurl>`\n`n!rank`\n`n!levelking`\n`n!botinfo`\n`n!uptime`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "管理者限定":
            embed = discord.Embed(title="管理者限定 <:kanrisya:1025283026520903720>",description="`n!purge <消したい文字の量>`\n`n!kick <@kickしたいメンバー>`\n`n!ban <@banしたいメンバー>`\n`n!unban <banを解除したいメンバーのID>`\n`n!nick <@nicknameを変えたいメンバー> <新たなnickname>`\n`n!dm <@メンバー> メッセージ`\n`n!lock <@ロックしたいロール> <#ロックしたいチャンネル>`\n`n!unlock <@ロックを解除したいロール> <#ロックを解除したいチャンネル>`\n`n!warn <@注意したいメンバー> <理由>`\n`n!removewarn <@注意を解除したいメンバー>`\n`n!warns <@注意を確認したいメンバー>`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "ヘルプホーム":
            embed = discord.Embed(title="helpコマンド || ヘルプホーム",description="このbotのコマンドを見るには下のセレクトメニューで選択したください",color=0x3683ff)
            embed.set_author(name="Ghanv Bot",url="https://discord.com/api/oauth2/authorize?client_id=1028629095120121888&permissions=8&scope=bot",icon_url="https://cdn.discordapp.com/attachments/1029677767941435472/1030384542915248158/disicon.png")
            embed.add_field(name="情報 <:jyouhou:1025282238541213767>",value="`11コマンド`")
            embed.add_field(name="管理者限定 <:kanrisya:1025283026520903720>",value="`12コマンド`")
            embed.add_field(name="面白い(笑) <:omosiroi:1025284268223643698>",value="`3コマンド`")
            embed.add_field(name="検索 <:kennsaku:1025284285235744800>",value="`5コマンド`")
            embed.add_field(name="フォートナイト <:fortnite:1025271326790910004>",value="`3コマンド`")
            embed.add_field(name="報告 <:houkoku:1025284996686155877>",value="`1コマンド`")
            embed.add_field(name="音楽 <:ongaku:1025285006765068338>",value="`12コマンド`")
            embed.add_field(name="翻訳 <:Google_Translate_Icon:1026017077473058857>",value="`2コマンド`")
            embed.add_field(name="お天気 🌦",value="`47コマンド`")
            embed.add_field(name="セッティング ⚙",value="`2コマンド`")
            embed.add_field(name="グローバル <:IQGroupGlobalicon:1033225964110495795>",value="`2コマンド`")
            embed.add_field(name="通貨 💸",value="`5コマンド`")
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "面白い(笑)":
            embed = discord.Embed(title="面白い(笑) <:omosiroi:1025284268223643698>",description="`n!meme`\n`n!omikuji`\n`n!imagegen <作りたい画像の名前>`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "検索":
            embed = discord.Embed(title="検索 <:kennsaku:1025284285235744800>",description="`n!wiki <検索キーワード>`\n`n!amazon <検索キーワード>`\n`n!youtube <検索キーワード>`\n`n!google <検索キーワード>`\n`n!disboard <検索キーワード>`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "フォートナイト":
            embed = discord.Embed(title="フォートナイト <:fortnite:1025271326790910004>",description="`n!shop`\n`n!item <検索したいスキンなど>`\n`n!map`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "報告":
            embed = discord.Embed(title="報告 <:houkoku:1025284996686155877>",description="`n!report <報告したい内容>`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "音楽":
            embed = discord.Embed(title="音楽 <:ongaku:1025285006765068338>",description="`n!play <再生したい曲名/Youtube URL>`\n`n!spoplay <再生したいspotifyの曲のURL>`\n`n!search <再生したい曲名>`\n`n!leave`\n`n!join`\n`n!skip`\n`n!pause`\n`n!resume`\n`n!loop`\n`n!queue`\n`n!volume`\n`n!nowplaying`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "翻訳":
            embed = discord.Embed(title="翻訳 <:Google_Translate_Icon:1026017077473058857>",description="`n!ja <日本語に翻訳したい英語>`\n`n!en <英語に翻訳したい日本語>`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "天気":
            embed = discord.Embed(title="天気 🌦",description="`OOの天気は？`と打つと\n今日, 明日, 明後日\nの天気情報を表示させます\n※例: `東京の天気は？`\n47都道府県対応しています!\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "セッティング":
            embed = discord.Embed(title="セッティング ⚙",description="`n!setwelcome <#指定したいチャンネル>`\n`n!setticket`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "グローバル":
            embed = discord.Embed(title="グローバル <:IQGroupGlobalicon:1033225964110495795>",description="`n!addGlobal`\n`n!removeGlobal`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        elif self.values[0] == "通貨":
            embed = discord.Embed(title="通貨 💸",description="`n!balance`\n`n!beg`\n`n!withdraw <引き出したい量>`\n`n!deposit <預けたい量>`\n`n!give <@渡したいメンバー> <渡したい量>`\n━━━━━━━━━━━━━━━━━━",color=0x3683ff)
            embed.add_field(name="作成者のSNS",value="Youtube <:youtube:1025960055180369980>\n[リンク](https://www.youtube.com/channel/UCGwHZwpTlsit7abi81AXT6A)\nTwitch <:twitch:1025280061718396970>\n[リンク](https://www.twitch.tv/dainy117)\nTwitter <:Twitter:1025281245279690802>\n[リンク](https://twitter.com/dainy_1san)\nサイト:link:\n[webサイト](https://sites.google.com/view/ghanvbot/)",inline=False)
            embed.set_footer(text="create by dainy#4297")
            await interaction.response.edit_message(embed=embed)
        

class SelectView(discord.ui.View):
    def __init__(self, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.add_item(Select())

def jst():
    now = datetime.datetime.utcnow()
    now = now + datetime.timedelta(hours=9)
    return now

@bot.command()
async def en(ctx, *, msg):
    embed = discord.Embed(title="翻訳",description="日本語から英語に翻訳中です...",color=0x3683ff)
    trans_now = await ctx.send(embed=embed)
    api_key = "dcd1b960-e1e6-f6e5-9557-b56dc91a45ba:fx"
    params = {
                "auth_key": api_key,
                "text": str(msg),
                "source_lang": "JA",
                "target_lang": "EN"
            }

    request = requests.post("https://api-free.deepl.com/v2/translate", data=params)
    result = request.json()
    embed = discord.Embed(title="英語",description=result["translations"][0]["text"],color=0x3683ff)
    await trans_now.edit(content="JA → EN\n", embed=embed)

@bot.command()
async def jp(ctx, *, msg):
    embed = discord.Embed(title="翻訳",description="英語から日本語に翻訳中です...",color=0x3683ff)
    trans_now = await ctx.send(embed=embed)
    api_key = "dcd1b960-e1e6-f6e5-9557-b56dc91a45ba:fx"
    params = {
                "auth_key": api_key,
                "text": str(msg),
                "source_lang": "EN",
                "target_lang": "JA"
            }

    request = requests.post("https://api-free.deepl.com/v2/translate", data=params)
    result = request.json()
    embed = discord.Embed(title="日本語",description=result["translations"][0]["text"],color=0x3683ff)
    await trans_now.edit(content="EN → JP\n", embed=embed)



@bot.listen("on_message")
async def on_message(message):
    if message.author.bot:
        return
    author = message.author
    guild = message.guild
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT xp FROM levels WHERE user = ? AND guild = ?", (author.id, guild.id,))
        xp = await cursor.fetchone()
        await cursor.execute("SELECT level FROM levels WHERE user = ? AND guild = ?", (author.id, guild.id,))
        level = await cursor.fetchone()

        if not xp or not level:
            await cursor.execute("INSERT INTO levels (level, xp, user, guild) VALUES (?, ?, ?, ?)", (0, 0, author.id, guild.id,))
            await bot.db.commit()
        
        try:
            xp = xp[0]
            level = level[0]
        except TypeError:
            xp = 0
            level = 0
        
        if level < 5:
            xp += random.randint(1, 3)
            await cursor.execute("UPDATE levels SET xp = ? WHERE user = ? AND guild = ?", (xp, author.id, guild.id,))
        else:
            rand = random.randint(1, (level//4))
            if rand == 1:
                xp += random.randint(1, 3)
                await cursor.execute("UPDATE levels SET xp = ? WHERE user = ? AND guild =?", (xp, author.id, guild.id,))
        if xp >= 100:
            level += 1
            await cursor.execute("UPDATE levels SET level = ? WHERE user = ? AND guild = ?", (level, author.id, guild.id,))
            await cursor.execute("UPDATE levels SET xp = ? WHERE user = ? AND guild = ?", (0, author.id, guild.id,))
            await message.channel.send(f"{author.mention}さんのレベルがアップしました。レベル: **{level}**")
    await bot.db.commit()

@bot.command(aliases=["rank"])
async def level(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT xp FROM levels WHERE user = ? AND guild = ?", (member.id, ctx.guild.id,))
        xp = await cursor.fetchone()
        await cursor.execute("SELECT level FROM levels WHERE user = ? AND guild = ?", (member.id, ctx.guild.id,))
        level = await cursor.fetchone()

        if not xp or not level:
            await cursor.execute("INSERT INTO levels (level, xp, user, guild) VALUES (?, ?, ?, ?)", (0, 0, member.id, ctx.guild.id,))
        
        try:
            xp = xp[0]
            level = level[0]
        except TypeError:
            xp = 0
            level = 0
        user_data = {
            "name": f"{member.name}#{member.discriminator}",
            "xp": xp,
            "level": level,
            "next_level_xp": 100,
            "percentage": xp,
        }

        background = Editor(Canvas((900, 300), color="#141414"))
        profile_picture = await load_image_async(str(member.avatar.url))
        profile = Editor(profile_picture).resize((150, 150)).circle_image()

        poppins = Font.poppins(size=40)
        poppins_small = Font.poppins(size=30)

        card_right_shape = [(600, 0), (750, 300), (900, 300), (900, 0)]

        background.polygon(card_right_shape, color="#FFFFFF")
        background.paste(profile, (30, 30))

        background.rectangle((30, 220), width=650, height=40, color="#FFFFFF")
        background.bar((30, 220), max_width=650, height=40, percentage=user_data["percentage"], color="#282828", radius=20,)
        background.text((200, 40), user_data["name"], font=poppins, color="#FFFFFF")
        
        background.rectangle((200, 100), width=350, height=2, fill="#FFFFFF")
        background.text(
            (200, 130),
            f"LEVEL! - {user_data['level']} | XP - {user_data['xp']}/{user_data['next_level_xp']}",
            font = poppins_small,
            color = "#FFFFFF",
        )

        file = discord.File(fp=background.image_bytes, filename="level.png")
        await ctx.send(file=file)

@bot.command()
async def levelking(ctx):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT level, xp, user FROM levels WHERE guild = ? ORDER BY level DESC, xp DESC LIMIT 10", (ctx.guild.id,))
        data = await cursor.fetchall()
        if data:
            em = discord.Embed(title="レベルのランキング")
            count = 0
            for table in data:
                count += 1
                user = ctx.guild.get_member(table[2])
                em.add_field(name=f"{count} - {user.name}", value=f"レベル-**{table[0]}** | 経験値-**{table[1]}**", inline=False)
            return await ctx.send(embed=em)
        return await ctx.send("ランキングが取得できませんでした")

@bot.command()
async def lock(ctx, role:discord.Role, channel:discord.TextChannel):
    role = role or ctx.guild.default_role
    channel = channel or ctx.channel
    async with ctx.typing():
        overwrite = channel.overwrites_for(role)
        overwrite.send_messages = False
        await channel.set_permissions(role, overwrite=overwrite)
        lock_embed = discord.Embed(
        title= ("ロック"),
        description= (f"**{channel.mention}** は **{role}** のロックが解除されました"),
        colour=0x00FFF5,
        )        
        lock_embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar.url)
        lock_embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
        lock_embed.set_thumbnail(url=ctx.guild.icon.url)    
        await ctx.channel.send(embed=lock_embed, delete_after=10)
        print("ロックしました")
     

@bot.command()
async def unlock(ctx, role:discord.Role, channel:discord.TextChannel):
    role = role or ctx.guild.default_role
    channel = channel or ctx.channel
    async with ctx.typing():
            overwrite = channel.overwrites_for(role)
            overwrite.send_messages = True
            await channel.set_permissions(role, overwrite=overwrite)
            unlock_embed = discord.Embed(
            title= ("アンロック"),
            description= (f"**{channel.mention}** は **{role}** のロックが解除されました"),
            colour=0x00FFF5,
            )        
            unlock_embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar.url)
            unlock_embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
            unlock_embed.set_thumbnail(url=ctx.guild.icon.url)    
            await ctx.channel.send(embed=unlock_embed, delete_after=10)
            print("アンロックしました")

@bot.event
async def on_member_join(member):
    with open('guilds.json', 'r', encoding='utf-8') as f:
        guilds_dict = json.load(f)
    channel_id = guilds_dict[str(member.guild.id)]
    
    background = Editor("bg.jpg")
    profile_image = await load_image_async(str(member.avatar.url))
    
    profile = Editor(profile_image).resize((150, 150)).circle_image()
    poppins = Font.poppins(size=50, variant="bold")
    
    poppins_small = Font.poppins(size=20, variant="light")
    
    background.paste(profile, (325, 90))
    background.ellipse((325, 90), 150, 150, outline="white", stroke_width=5)
    
    background.text((400, 260), f"welcome to {member.guild.name}", color="white", font=poppins, align="center")
    background.text((400,325), f"{member.name}", color="white", font=poppins_small, align="center")
    
    file = File(fp=background.image_bytes, filename="pic.jpg")
    guild = member.guild 
    member_count = guild.member_count
    user_count = sum(1 for member in guild.members if not member.bot)
    bot_count = sum(1 for member in guild.members if member.bot)
    embed = discord.Embed(title="WELCOME",description=f"ようこそ {member.mention} さん\nサーバーメンバー数: {member_count} \nユーザ数： {user_count} \nBOT数： {bot_count} \nアカウント作成日: {member.created_at} \nサーバー参加時間: {member.joined_at} \nアバター: [URL]({member.avatar.url})",color=0x0077ff)
    embed.set_image(url="attachment://pic.jpg")
    await bot.get_channel(int(channel_id)).send(embed=embed, file=file)

@bot.event
async def on_member_remove(member):
    
    with open('guilds.json', 'r', encoding='utf-8') as f:
        guilds_dict = json.load(f)
    channel_id = guilds_dict[str(member.guild.id)]
    
    background = Editor("bg.jpg")
    profile_image = await load_image_async(str(member.avatar.url))
    
    profile = Editor(profile_image).resize((150, 150)).circle_image()
    poppins = Font.poppins(size=50, variant="bold")
    
    poppins_small = Font.poppins(size=20, variant="light")
    
    background.paste(profile, (325, 90))
    background.ellipse((325, 90), 150, 150, outline="white", stroke_width=5)
    
    background.text((400, 260), f"byebye to {member.guild.name}", color="white", font=poppins, align="center")
    background.text((400,325), f"{member.name}", color="white", font=poppins_small, align="center")
    
    file = File(fp=background.image_bytes, filename="pic.jpg")
    guild = member.guild 
    member_count = guild.member_count
    user_count = sum(1 for member in guild.members if not member.bot)
    bot_count = sum(1 for member in guild.members if member.bot)
    embed = discord.Embed(title="BYEBYE",description=f"バイバイ {member.mention} さん\nサーバーメンバー数: {member_count} \nユーザ数： {user_count} \nBOT数： {bot_count} \nアカウント作成日: {member.created_at} \nアバター: [URL]({member.avatar.url})",color=0x0077ff)
    embed.set_image(url="attachment://pic.jpg")
    await bot.get_channel(int(channel_id)).send(embed=embed, file=file)


@bot.command()
async def setwelcome(ctx, channel: discord.TextChannel):
    with open('guilds.json', 'r', encoding='utf-8') as f:
        guilds_dict = json.load(f)

    guilds_dict[str(ctx.guild.id)] = str(channel.id)
    with open('guilds.json', 'w', encoding='utf-8') as f:
        json.dump(guilds_dict, f, indent=4, ensure_ascii=False)
    
    await ctx.send(f'{ctx.message.guild.name} のウェルカム チャンネルを `{channel.name}` に設定しました')


#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━イベント━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ヘルプ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.command(aliases=["info", "about", "?"])
async def help(ctx):
  embed = discord.Embed(title="helpコマンド || ヘルプホーム",description="このbotのコマンドを見るには下のセレクトメニューで選択したください",color=0x3683ff)
  embed.set_author(name="Ghanv Bot",url="https://discord.com/api/oauth2/authorize?client_id=1028629095120121888&permissions=8&scope=bot",icon_url=f"{bot.user.avatar.url}")
  embed.add_field(name="情報 <:jyouhou:1025282238541213767>",value="`11コマンド`")
  embed.add_field(name="管理者限定 <:kanrisya:1025283026520903720>",value="`12コマンド`")
  embed.add_field(name="面白い(笑) <:omosiroi:1025284268223643698>",value="`3コマンド`")
  embed.add_field(name="検索 <:kennsaku:1025284285235744800>",value="`5コマンド`")
  embed.add_field(name="フォートナイト <:fortnite:1025271326790910004>",value="`3コマンド`")
  embed.add_field(name="報告 <:houkoku:1025284996686155877>",value="`1コマンド`")
  embed.add_field(name="音楽 <:ongaku:1025285006765068338>",value="`12コマンド`")
  embed.add_field(name="翻訳 <:Google_Translate_Icon:1026017077473058857>",value="`2コマンド`")
  embed.add_field(name="お天気 🌦",value="`47コマンド`")
  embed.add_field(name="セッティング ⚙",value="`2コマンド`")
  embed.add_field(name="グローバル <:IQGroupGlobalicon:1033225964110495795>",value="`2コマンド`")
  embed.add_field(name="通貨 💸",value="`5コマンド`")
  embed.set_footer(text="create by dainy#4297", icon_url=f"{ctx.author.avatar.url}")
  await ctx.send(embed=embed, view=SelectView())

    
@bot.slash_command(description="helpコマンドを表示させます")
async def help(ctx):
  embed = discord.Embed(title="helpコマンド || ヘルプホーム",description="このbotのコマンドを見るには下のセレクトメニューで選択したください",color=0x3683ff)
  embed.set_author(name="Ghanv Bot",url="https://discord.com/api/oauth2/authorize?client_id=1028629095120121888&permissions=8&scope=bot",icon_url=f"{bot.user.avatar.url}")
  embed.add_field(name="情報 <:jyouhou:1025282238541213767>",value="`11コマンド`")
  embed.add_field(name="管理者限定 <:kanrisya:1025283026520903720>",value="`12コマンド`")
  embed.add_field(name="面白い(笑) <:omosiroi:1025284268223643698>",value="`3コマンド`")
  embed.add_field(name="検索 <:kennsaku:1025284285235744800>",value="`5コマンド`")
  embed.add_field(name="フォートナイト <:fortnite:1025271326790910004>",value="`3コマンド`")
  embed.add_field(name="報告 <:houkoku:1025284996686155877>",value="`1コマンド`")
  embed.add_field(name="音楽 <:ongaku:1025285006765068338>",value="`12コマンド`")
  embed.add_field(name="翻訳 <:Google_Translate_Icon:1026017077473058857>",value="`2コマンド`")
  embed.add_field(name="お天気 🌦",value="`47コマンド`")
  embed.add_field(name="セッティング ⚙",value="`2コマンド`")
  embed.add_field(name="グローバル <:IQGroupGlobalicon:1033225964110495795>",value="`2コマンド`")
  embed.add_field(name="通貨 💸",value="`5コマンド`")
  embed.set_footer(text="create by dainy#4297", icon_url=f"{ctx.author.avatar.url}")
  await ctx.respond(embed=embed, view=SelectView())

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ヘルプ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━情報━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class InfoButtons(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
    @discord.ui.button(label="名前",style=discord.ButtonStyle.green) # or .primary
    async def b1_button(self,button:discord.ui.Button,interaction:discord.Interaction):
        button.disabled=False
        embed = discord.Embed(title="名前",description=f"{bot.user.name}")
        await interaction.response.edit_message(embed=embed,view=self)
    @discord.ui.button(label="ID",style=discord.ButtonStyle.green) # or .secondary/.grey
    async def b2_button(self,button:discord.ui.Button,interaction:discord.Interaction):
        button.disabled=False
        embed = discord.Embed(title="ID",description=f"{bot.user.id}")
        await interaction.response.edit_message(embed=embed,view=self)
    @discord.ui.button(label="バージョン",style=discord.ButtonStyle.green) # or .success
    async def b3_button(self,button:discord.ui.Button,interaction:discord.Interaction):
        button.disabled=False
        embed = discord.Embed(title="バージョン",description=f"{discord.__version__}")
        await interaction.response.edit_message(embed=embed,view=self)
    @discord.ui.button(label="PING",style=discord.ButtonStyle.green) # or .danger
    async def b4_button(self,button:discord.ui.Button,interaction:discord.Interaction):
        button.disabled=False
        embed = discord.Embed(title="PING",description=f"{round(bot.latency *1000)}")
        await interaction.response.edit_message(embed=embed,view=self)
    @discord.ui.button(label="サーバー参加人数",style=discord.ButtonStyle.green) # or .danger
    async def b5_button(self,button:discord.ui.Button,interaction:discord.Interaction):
        button.disabled=False
        embed = discord.Embed(title="サーバー参加人数",description=f"{len(bot.guilds)}サーバー")
        await interaction.response.edit_message(embed=embed,view=self)
    @discord.ui.button(label="ユーザー数",style=discord.ButtonStyle.green) # or .danger
    async def b6_button(self,button:discord.ui.Button,interaction:discord.Interaction):
        button.disabled=False
        embed = discord.Embed(title="ユーザー数",description=f"{len(bot.users)}ユーザー数")
        await interaction.response.edit_message(embed=embed,view=self)
@bot.command(description="botの情報を表示させます")
async def botinfo(ctx):
  embed = discord.Embed(title="bot情報",description="下のボタンのどれかをクリックしてください")
  await ctx.send(embed=embed,view=InfoButtons())


@bot.command()
async def ping(ctx):
    embed=discord.Embed(title="現在のPing", description=f"pingは\n```{round(bot.latency *1000)}```です。", color=0x2e5bff)
    await ctx.send(embed=embed)

start_time = time.time()

@bot.command()
async def uptime(ctx):
        current_time = time.time()
        difference = int(round(current_time - start_time))
        text = str(datetime.timedelta(seconds=difference))
        embed = discord.Embed(colour=ctx.message.author.top_role.colour)
        embed.add_field(name="Bot稼働時間", value=text)
        embed.set_footer(text="create by dainy#4297")
        try:
            await ctx.send(embed=embed)
        except discord.HTTPException:
            await ctx.send("現在の稼働時間: " + text)

@bot.command()
async def invite(ctx, ID=None):
    if ID == None:
        em = discord.Embed(title=f"{bot.user.name}の招待リンク",description=f"[招待はこちら](https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot)",color=0x2e5bff)
        await ctx.send(embed=em)
    else:
        embed=discord.Embed(title="招待URLを発行しました。",description=f"**[管理者権限付きで招待する](https://discord.com/oauth2/authorize?client_id={ID}&permissions=8&scope=bot)**\n\n**[権限を選択して招待する](https://discord.com/api/oauth2/authorize?client_id={ID}&permissions=2147483639&scope=bot)**\n\n**[権限なしで招待する](https://discord.com/api/oauth2/authorize?client_id={ID}&permissions=0&scope=bot)**",color=0x2e5bff)
        await ctx.channel.send(embed=embed)

@bot.command()
async def invites(ctx, user:discord.Member):
  totalInvites = 0
  for i in await ctx.guild.invites():
    if i.inviter == user:
      totalInvites += i.uses
  embed = discord.Embed(title="ユーザーの招待", color=discord.Colour.purple())
  embed.add_field(name="ユーザー", value=f"{user.mention}", inline=False)
  embed.add_field(name="回数", value=f"{totalInvites}回", inline=False)
  embed.set_footer(text=f"実行者: {ctx.author} ", icon_url=ctx.author.avatar.url)
  await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member=None):
    if member == None:
        member = ctx.author
    
    icon_url = member.avatar.url 
 
    avatarEmbed = discord.Embed(title = f"{member.name}\'のアバター", url=ctx.author.avatar.url, color = 0xFFA500)
 
    avatarEmbed.set_image(url = f"{icon_url}")
 
    avatarEmbed.timestamp = ctx.message.created_at 
 
    await ctx.send(embed = avatarEmbed)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━情報━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.command()
async def serverinfo(ctx):
  guild = ctx.message.guild
  roles =[role for role in guild.roles]
  text_channels = [text_channels for text_channels in guild.text_channels]
  embed = discord.Embed(title=f"{guild.name}info",color=0x3683ff)
  embed.add_field(name="管理者",value=f"{ctx.guild.owner}",inline=False)
  embed.add_field(name="ID",value=f"{ctx.guild.id}",inline=False)
  embed.add_field(name="チャンネル数",value=f"{len(text_channels)}",inline=False)
  embed.add_field(name="ロール数",value=f"{len(roles)}",inline=False)
  embed.add_field(name="サーバーブースター",value=f"{guild.premium_subscription_count}",inline=False)
  embed.add_field(name="メンバー数",value=f"{guild.member_count}",inline=False)
  embed.add_field(name="サーバー設立日",value=f"{guild.created_at}",inline=False)
  embed.set_footer(text=f"実行者 : {ctx.author} ")
  await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx):
  embed = discord.Embed(title=f"user {ctx.author.name}",description="userinfo",color=0x3683ff)
  embed.add_field(name="名前",value=f"{ctx.author.mention}",inline=False)
  embed.add_field(name="ID",value=f"{ctx.author.id}",inline=False)
  embed.add_field(name="ACTIVITY",value=f"{ctx.author.activity}",inline=False)
  embed.add_field(name="TOP_ROLE",value=f"{ctx.author.top_role}",inline=False)
  embed.add_field(name="discriminator",value=f"#{ctx.author.discriminator}",inline=False)
  embed.add_field(name="サーバー参加",value=f"{ctx.author.joined_at.strftime('%d.%m.%Y, %H:%M Uhr')}",inline=False)
  embed.add_field(name="アカウント作成",value=f"{ctx.author.created_at.strftime('%d.%m.%Y, %H:%M Uhr')}",inline=False)
  embed.set_thumbnail(url=f"{ctx.author.avatar.url}")
  embed.set_footer(text=f"実行者 : {ctx.author} ")
  await ctx.send(embed=embed)

@bot.command()
async def url(ctx, url=None):
    if url == None:
        em = discord.Embed(title="エラー",description="URLを入力してください",color=0x3683ff)
        await ctx.reply(embed=em)

    else:
        embed=discord.Embed(title=f"{url}に関する検査結果",description=f"**{url}**に関する検査結果は[こちら](https://safeweb.norton.com/report/show?url={url})",color=0x2e5bff)
        await ctx.send(embed=embed)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━情報━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

citycodes = {
    "北海道":"016010",
    "青森":"020010",
    "岩手":"030010",
    "宮城":"040010",
    "秋田":"050010",
    "山形":"060010",
    "福島":"070010",
    "茨城":"080010",
    "栃木":"090010",
    "群馬":"100010",
    "埼玉":"110010",
    "千葉":"120010",
    "東京":"130010",
    "神奈川":"140010",
    "新潟":"150010",
    "富山":"160010",
    "石川":"170010",
    "福井":"180010",
    "山形":"190010",
    "長野":"200010",
    "岐阜":"210010",
    "静岡":"220010",
    "愛知":"230010",
    "三重":"240010",
    "滋賀":"250010",
    "京都":"260010",
    "大阪":"270000",
    "兵庫":"280010",
    "奈良":"290010",
    "和歌山":"300010",
    "鳥取":"310010",
    "島根":"320010",
    "岡山":"330010",
    "広島":"340010",
    "山口":"350010",
    "徳島":"360010",
    "香川":"370000",
    "愛媛":"380010",
    "高知":"390010",
    "福島":"400010",
    "佐賀":"410010",
    "長崎":"420010",
    "熊本":"430010",
    "大分":"440010",
    "宮崎":"450010",
    "鹿児島":"460010",
    "沖縄":"471010",    
}



@bot.listen("on_message")
async def on_message(message):
    #Botのメッセージは無視
    if message.author.bot:
        return
    reg_res = re.compile(u"(.+)の天気は？").search(message.content)
    if reg_res:
      if reg_res.group(1) in citycodes.keys():
        citycode = citycodes[reg_res.group(1)]
        resp = Request(f'https://weather.tsukumijima.net/api/forecast/city/{citycode}', headers={'User-Agent': 'Mozilla/5.0'})
        resp = urlopen(resp).read()
        resp = json.loads(resp.decode("utf-8"))
        embed = discord.Embed(title= resp["title"],description= "__【お天気情報：**" + resp["location"]["city"] + "**】__\n",color=0x3683ff)
        for f in resp["forecasts"]:
         embed.add_field(name=f["dateLabel"] + "：",value=f["telop"],inline=True)
         embed.add_field(name="天気：",value=f["detail"]["weather"],inline=True)
         embed.add_field(name="風：",value=f["detail"]["wind"],inline=True)
        embed.add_field(name="説明：",value="```" + resp["description"]["bodyText"] + "```",inline=False)
        string = resp["forecasts"][0]["image"]["url"]
        embed.set_image(url=string[0:45] + "png")
        embed.set_thumbnail(url=resp["forecasts"][0]["image"]["url"])
        await message.channel.send(embed=embed)
      else:
        await message.channel.send("そこの天気はわかりません...")

@bot.command()
async def omikuji(ctx):
  result = ["大吉", "中吉", "小吉", "凶", "大凶"]
  embed = discord.Embed(title="おみくじ結果",description=random.choice(result))
  await ctx.send(embed=embed)

@bot.command(pass_content=True)
@commands.has_permissions(administrator=True)
async def nick(ctx, member: discord.Member, nick):
  await member.edit(nick=nick)
  embed = discord.Embed(title="ニックネームを変更しました",description=f"変更された人物: {member.mention}",color=0xffffff)
  await ctx.send(embed=embed)


        
@bot.command()
@commands.has_permissions(administrator=True)
@commands.has_permissions(manage_channels=True)
async def kick(ctx, member: discord.Member, *, reason=None):
  await member.kick(reason=reason)
  await ctx.send(f"ユーザー {member.mention} をkickしました")

@bot.command()
@commands.has_permissions(administrator=True)
@commands.has_permissions(manage_channels=True)
async def ban(ctx, member: discord.Member, *, reason=None):
  await member.ban(reason=reason)
  await ctx.send(f"ユーザー {member.mention} をbanしました")

@bot.command()
@commands.has_permissions(administrator=True)
@commands.has_permissions(manage_channels=True)
async def unban(ctx, *, member):
    bannedUsers = await ctx.guild.bans()
    name, discriminator = member.split("#")

    for ban in bannedUsers:
        user = ban.user

        if(user.name, user.discriminator) == (name, discriminator):
            await ctx.guild.unban(user)
            await ctx.send(f"{user.mention} banを解除しました")

@bot.command()
async def disboard(ctx, search=None):
    if search == None:
        em = discord.Embed(title="エラー",description="タグを入力してください",color=0x3683ff)
        await ctx.reply(embed=em)

    else:
        embed=discord.Embed(title=f"{search}に関するサーバーを検索",description=f"**{search}**に関するサーバーは[こちら](https://disboard.org/ja/servers/tag/{search})",color=0x2e5bff)
        await ctx.send(embed=embed)

@bot.command()
async def shop(ctx):
        viewurl=Buttons()
        viewurl.add_item(discord.ui.Button(label="アイテムショップ",style=discord.ButtonStyle.link,url="https://fn-db.com/itemshop/", emoji="<:fortnite:1025271326790910004>"))
        embed = discord.Embed(title='Fortnite Item Shop',color=0x6a5acd)
        embed.set_image(url='https://api.nitestats.com/v1/shop/image')
        embed.set_footer(text=f"コマンド実行者: {ctx.author}", icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed,view=viewurl)

@bot.command(pass_context=True)
async def meme(ctx):
    embed = discord.Embed(title="meme", description="^~^",color=0x3683ff)

    async with aiohttp.ClientSession() as cs:
        async with cs.get('https://www.reddit.com/r/dankmemes/new.json?sort=hot') as r:
            res = await r.json()
            embed.set_image(url=res['data']['children'] [random.randint(0, 25)]['data']['url'])
            await ctx.send(embed=embed)

@bot.command()
async def youtube(ctx, search=None):
    if search == None:
        em = discord.Embed(title="エラー",description="さがしたい動画などのワードを入力してください",color=0x3683ff)
        await ctx.reply(embed=em)
        
    else:
        embed=discord.Embed(title=f"{search}を検索",description=f"**{search}**の検索結果は[こちら](https://www.youtube.com/results?search_query={search})",color=0x2e5bff)
        await ctx.send(embed=embed)

@bot.command()
async def google(ctx, search=None):
    if search == None:
        em = discord.Embed(title="エラー",description="さがしたい物などのワードを入力してください",color=0x3683ff)
        await ctx.reply(embed=em)
        
    else:
        embed=discord.Embed(title=f"{search}を検索",description=f"**{search}**の検索結果は[こちら](https://www.google.co.jp/search?q={search}&safe=active)",color=0x2e5bff)
        await ctx.send(embed=embed)

@bot.command()
async def amazon(ctx, search=None):
    if search == None:
        em = discord.Embed(title="エラー",description="さがしたい商品などのワードを入力してください",color=0x3683ff)
        await ctx.reply(embed=em)
      
    else:
        embed=discord.Embed(title=f"{search}を検索",description=f"**{search}**の検索結果は[こちら](https://www.amazon.co.jp/s?k={search})",color=0x2e5bff)
        await ctx.send(embed=embed)
        
@bot.command()
async def wiki(ctx, search=None):
    if search == None:
        em = discord.Embed(title="エラー",description="検索したいワードを入力してください",color=0x3683ff)
        await ctx.reply(embed=em)
        
    else:
        embed=discord.Embed(title=f"{search}に関するワードを検索",description=f"**{search}**に関するはワード[こちら](https://ja.wikipedia.org/wiki/{search})",color=0x2e5bff)
        await ctx.send(embed=embed)
        
@bot.command()
async def item(ctx, *, args=None):
    if args == None:
        em = discord.Embed(title="Error",description="検索したいアイテム名を打ってください。",color=0x3683ff)
        await ctx.send(embed=em)
    else:
        response = requests.get(f'https://fortnite-api.com/v2/cosmetics/br/search/all?name={args}&matchMethod=starts&language=ja&searchLanguage=ja').json()

        if response['status'] == 200:

            for item in response['data']:
                try:
                    item_set = item["set"]["value"]
                except:
                    item_set = 'このアイテムはセットではありません。'
                try:
                    item_introduction = item['introduction']['text']
                except:
                    item_introduction = 'データがありません。'

                embed = discord.Embed(title=item['type']['displayValue'],colour=0x6a5acd,timestamp=ctx.message.created_at)
                if item['images']['icon'] != None:
                    embed.set_thumbnail(url=item['images']['icon'])
                embed.add_field(name="アイテム名",value=f'{item["name"]}')
                embed.add_field(name="ID",value=f'{item["id"]}')
                embed.add_field(name="説明", value=f'{item["description"]}')
                embed.add_field(name="レアリティ", value=f'{item["rarity"]["displayValue"]}')
                embed.add_field(name="セット",value=f'{item_set}')
                embed.add_field(name="導入日",value=f'{item_introduction}')
                embed.set_footer(text=f"コマンド実行者: {ctx.author}", icon_url=ctx.author.avatar.url)
                await ctx.send(embed=embed)

        elif response['status'] == 400:
            error = response['error']
            embed = discord.Embed(title=':no_entry_sign:｜Error',description=f'``{error}``',color=0x3683ff)
            embed.set_footer(text=f"コマンド実行者: {ctx.author}", icon_url=ctx.author.avatar.url)
            await ctx.send(embed=embed)

        elif response['status'] == 404:
            error = response['error']
            embed = discord.Embed(title=':no_entry_sign:｜Error', description="アイテムが存在しませんでした。",color=0x3683ff)
            embed.set_footer(text=f"コマンド実行者: {ctx.author}", icon_url=ctx.author.avatar.url)
            await ctx.send(embed=embed)

@bot.command()
async def map(ctx):
    data = requests.get('https://fortnite-api.com/v1/map?language=ja').json()
    em = discord.Embed(title="フォートナイトのマップ", colour=0x6a5acd)
    em.set_image(url=data['data']['images']['pois'])
    em.set_footer(text=f"コマンド実行者: {ctx.author}", icon_url=ctx.author.avatar.url)
    await ctx.send(embed=em)



@bot.command()
async def report(ctx, search=None):
    if search == None:
        em = discord.Embed(title="エラー",description="不具合内容を書いてください",color=0x3683ff)
        await ctx.reply(embed=em)
        await bot.change_presence(activity=discord.Game(name=f"{len(bot.guilds)}server | {len(bot.users)}User｜ver.{discord.__version__}"), status=discord.Status.online)
    else:
        CHANNEL_ID = 1037998685948227636
        channel = bot.get_channel(CHANNEL_ID)
        embed = discord.Embed(title="不具合を通知しました", description=f"```\n{search}\n```", color=0x3683ff)
        embed.add_field(name="サーバー", value=ctx.guild.name, inline=True)
        embed.add_field(name="ユーザー", value=ctx.author.name, inline=True)
        await channel.send(embed=embed)
        embed=discord.Embed(title="エラー内容を送信しました",description=f"{search}を送信しました",color=0x2e5bff)
        await ctx.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after): 
    if member.guild.id == 1029664427416490024 and (before.channel != after.channel):
        now = jst()
        alert_channel = bot.get_channel(1037998685948227636)
        if before.channel is None: 
            msg1 = discord.Embed(title="***VC-JOIN***",description=f"`{member.name}`",color=0x3683ff)
            msg1.add_field(name="時間",value=now.strftime('%Y /%m / %d　 %H : %M : %S'),inline=True)
            msg1.add_field(name="チャンネル",value=f'{after.channel.name}',inline=True)
            await alert_channel.send(embed=msg1)
        elif after.channel is None: 
            msg2 = discord.Embed(title="***VC-LEAVE***",description=f"`{member.name}`",color=0x3683ff)
            msg2.add_field(name="時間",value=now.strftime('%Y /%m / %d　 %H : %M : %S'),inline=True)
            msg2.add_field(name="チャンネル",value=f'{before.channel.name}',inline=True)
            await alert_channel.send(embed=msg2)

@bot.command()
@commands.has_permissions(administrator=True)
@commands.has_permissions(manage_channels=True)
async def purge(ctx, target:int):
  channel = ctx.message.channel
  deleted = await channel.purge(limit=target)
  await ctx.send(f"{len(deleted)}メッセージを削除しました", delete_after=10)

@bot.command(name = 'dm')
@commands.has_permissions(administrator=True)
@commands.has_permissions(manage_channels=True)
async def dm(ctx, member: discord.Member, *, content):
    channel = await member.create_dm()
    await channel.send(content)

@bot.command()
async def imagegen(ctx, *, prompt: str):
    ETA = int(time.time() + 60)
    msg = await ctx.send(f"画像を作っています 残り時間: <t:{ETA}:R>")
    async with aiohttp.request("POST", "https://backend.craiyon.com/generate", json={"prompt": prompt}) as resp:
        r = await resp.json()
        images = r["images"]
        image = BytesIO(base64.decodebytes(images[0].encode("utf-8")))
        return await msg.edit(content="create by dainy#4297", file=discord.File(image, "generatedImage.png"), view=DropdownView(msg, images, ctx.author.id))

class Dropdown(discord.ui.Select):
    def __init__(self, message, images, user):
        self.message = message
        self.images = images
        self.user = user

        options=[
            discord.SelectOption(label="1"),
            discord.SelectOption(label="2"),
            discord.SelectOption(label="3"),
            discord.SelectOption(label="4"),
            discord.SelectOption(label="5"),
            discord.SelectOption(label="6"),
            discord.SelectOption(label="7"),
            discord.SelectOption(label="8"),
            discord.SelectOption(label="9"),
        ]

        super().__init__(
            placeholder="画像を選択できます",
            min_values=1,
            max_values=1,
            options=options,
            )
    async def callback(self, interaction: discord.Interaction):
            if not int(self.user) == int(interaction.user.id):
                await interaction.response.send_message("あなたはこのメッセージの作成者ではありません!", ephemeral=True)
            selection = int(self.values[0])-1
            image = BytesIO(base64.decodebytes(self.images[selection].encode("utf-8")))
            return await interaction.response.edit_message(content="create by dainy#4297", file=discord.File(image, "generatedImage.png"), view=DropdownView(self.message, self.images, self.user))

class DropdownView(discord.ui.View):
    def __init__(self, message, images, user):
        super().__init__()
        self.message = message
        self.images = images
        self.user = user
        self.add_item(Dropdown(self.message, self.images, self.user))

#---------------------------------------------------------slashcommand----------------------------------------------------------    

@bot.slash_command(description="メッセージを削除できます")
@commands.has_permissions(administrator=True)
@commands.has_permissions(manage_channels=True)
async def purge(ctx, メッセージ: Option(int, description="消したい量を入力してください", required = True)):
  await ctx.defer()
  await ctx.channel.purge(limit=メッセージ)



@bot.slash_command(pass_content=True, description="ニックネームを変更します")
@commands.has_permissions(administrator=True)
async def nick(ctx, メンバー: discord.Member, ニックネーム: Option(description="ニックネームを入力してください")):
  await メンバー.edit(nick=ニックネーム)
  embed = discord.Embed(title="ニックネームを変更しました",description=f"変更された人物: {メンバー.mention}",color=0x3683ff)
  await ctx.respond(embed=embed)
  
@bot.slash_command(description="メンバーをキックします")
@commands.has_permissions(administrator=True)
@commands.has_permissions(manage_channels=True)
async def kick(ctx, メンバー: discord.Member, *, 理由=None):
  await メンバー.kick(reason=理由)
  await ctx.respond(f"ユーザー {メンバー.mention} をkickしました")

@bot.slash_command(description="メンバーをバンします")
@commands.has_permissions(administrator=True)
@commands.has_permissions(manage_channels=True)
async def ban(ctx, メンバー: discord.Member, *, 理由=None):
  await メンバー.ban(reason=理由)
  await ctx.respond(f"ユーザー {メンバー.mention} をbanしました")

@bot.slash_command(description="メンバーのバンを解除します")
@commands.has_permissions(administrator=True)
@commands.has_permissions(manage_channels=True)
async def unban(ctx, *, メンバー):
    bannedUsers = await ctx.guild.bans()
    name, discriminator = メンバー.split("#")

    for ban in bannedUsers:
        user = ban.user

        if(user.name, user.discriminator) == (name, discriminator):
            await ctx.guild.unban(user)
            await ctx.respond(f"{user.mention} banを解除しました")

@bot.slash_command(description="disboardを検索します")
async def disboard(ctx, 検索=None):
    if 検索 == None:
        em = discord.Embed(title="エラー",description="タグを入力してください",color=0x3683ff)
        await ctx.respond(embed=em)

    else:
        embed=discord.Embed(title=f"{検索}に関するサーバーを検索",description=f"**{検索}**に関するサーバーは[こちら](https://disboard.org/ja/servers/tag/{検索})",color=0x2e5bff)
        await ctx.respond(embed=embed)


@bot.slash_command(description="youtubeを検索します")
async def youtube(ctx, 検索=None):
    if 検索 == None:
        em = discord.Embed(title="エラー",description="さがしたい動画などのワードを入力してください",color=0x3683ff)
        await ctx.respond(embed=em)
        
    else:
        embed=discord.Embed(title=f"{検索}を検索",description=f"**{検索}**の検索結果は[こちら](https://www.youtube.com/results?search_query={検索})",color=0x2e5bff)
        await ctx.respond(embed=embed)

@bot.slash_command(description="googleを検索します")
async def google(ctx, 検索=None):
    if 検索 == None:
        em = discord.Embed(title="エラー",description="さがしたい物などのワードを入力してください",color=0x3683ff)
        await ctx.respond(embed=em)
        
    else:
        embed=discord.Embed(title=f"{検索}を検索",description=f"**{検索}**の検索結果は[こちら](https://www.google.co.jp/search?q={検索}&safe=active)",color=0x2e5bff)
        await ctx.respond(embed=embed)

@bot.slash_command(description="amazonを検索します")
async def amazon(ctx, 検索=None):
    if 検索 == None:
        em = discord.Embed(title="エラー",description="さがしたい商品などのワードを入力してください",color=0x3683ff)
        await ctx.respond(embed=em)
      
    else:
        embed=discord.Embed(title=f"{検索}を検索",description=f"**{検索}**の検索結果は[こちら](https://www.amazon.co.jp/s?k={検索})",color=0x2e5bff)
        await ctx.respond(embed=embed)
        
@bot.slash_command(description="wikiを検索します")
async def wiki(ctx, 検索=None):
    if 検索 == None:
        em = discord.Embed(title="エラー",description="検索したいワードを入力してください",color=0x3683ff)
        await ctx.respond(embed=em)
        
    else:
        embed=discord.Embed(title=f"{検索}に関するワードを検索",description=f"**{検索}**に関するはワード[こちら](https://ja.wikipedia.org/wiki/{検索})",color=0x2e5bff)
        await ctx.respond(embed=embed)

@bot.slash_command(description="botの招待リンクを発行します")
async def invite(ctx, id=None):
    if id == None:
        em = discord.Embed(title=f"{bot.user.name}の招待リンク",description=f"[招待はこちら](https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot)",color=0x2e5bff)
        await ctx.respond(embed=em)
    else:
        embed=discord.Embed(title="招待URLを発行しました。",description=f"**[管理者権限付きで招待する](https://discord.com/oauth2/authorize?client_id={id}&permissions=8&scope=bot)**\n\n**[権限を選択して招待する](https://discord.com/api/oauth2/authorize?client_id={id}&permissions=2147483639&scope=bot)**\n\n**[権限なしで招待する](https://discord.com/api/oauth2/authorize?client_id={id}&permissions=0&scope=bot)**",color=0x2e5bff)
        await ctx.respond(embed=embed)

@bot.slash_command(description="招待回数を確認できます")
async def invites(ctx, ユーザー:discord.Member):
  totalInvites = 0
  for i in await ctx.guild.invites():
    if i.inviter == ユーザー:
      totalInvites += i.uses
  embed = discord.Embed(title="ユーザーの招待", color=discord.Colour.purple())
  embed.add_field(name="ユーザー", value=f"{ユーザー.mention}", inline=False)
  embed.add_field(name="回数", value=f"{totalInvites}回", inline=False)
  embed.set_footer(text=f"実行者: {ctx.author} ", icon_url=ctx.author.avatar.url)
  await ctx.respond(embed=embed)

@bot.slash_command(description="pingを表示させます")
async def ping(ctx):
    embed=discord.Embed(title="現在のPing", description=f"pingは\n```{round(bot.latency *1000)}```です。", color=0x2e5bff)
    await ctx.respond(embed=embed)

bot.run(config['token'])