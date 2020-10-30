from discord.ext import commands
import discord
import subprocess
import os
import sqlite3
from mcuuid.api import GetPlayerData
from mcrcon import MCRcon
from dotenv import load_dotenv


load_dotenv()

SERVERADDRESS: str = os.environ["serverAddress"]
PASSWORD: str = os.environ["password"]
DISCORDTOKEN: str = os.environ["discordToken"]
LEVEL1: list[int] = []
for i in os.environ["level1"].split(","):
    LEVEL1.append(i)
LEVEL2: list[int] = []
for i in os.environ["level2"].split(","):
    LEVEL2.append(i)


db = sqlite3.connect("bot.db")
client = commands.Bot(command_prefix="!")


def bash(bash_command: str):
    """runs bash command on the current system
    """
    # not used for now but can be useful if the bot is running on the same
    # system as the server. such as seeing ram usage ect

    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    output = output.decode('ascii')


def command(cmd: str) -> str:
    """ runs the minecraft command \"cmd\" on the server

    Returns a string containing the results of the command
    """
    with MCRcon(SERVERADDRESS, PASSWORD) as mcr:
        response = mcr.command(cmd)
    return response


def has_roles(ctx, roles: list):
    """Checks if a user has at least 1 of the roles in roles
    """
    for r in ctx.author.roles:
        if r.name in roles:
            return True
    return False


def validated_users(users: list[int]):
    cursor = db.cursor("")
    cursor.execute(f"SELECT * FROM users WHERE discord_id IN ?",
                   (users))
    rows = cursor.fetchall()
    cursor.close()
    return rows


def add_to_whitelist(username: str, disc_user: discord.User):
    command("whitelist add " + username)
    sql = "INSERT INTO users(discord_id, minecraft_uuid) VALUES(?,?)"
    uuid = GetPlayerData(username).uuid
    cursor = db.cursor("")
    cursor.execute(disc_user.id, uuid)


@client.command(brief="gets the status of the system the server is "
                      "running on",
                enabled=False)
async def status(ctx):
    """gets the monit status of the current system
    """

    output = bash("monit status")

    output = output.split('\n\n')

    for item in output[:4]:
        await ctx.send('```\n' + item + '\n```')
    # for i in output.decode('ascii').split("\n"):
    #     if i:
    #         await ctx.send(i)


@client.command(brief="sends a message in the minecraft chat")
@commands.check(lambda ctx: has_roles(ctx, LEVEL1 + LEVEL2))
async def say(ctx, *, cmd):
    command("/say " + ctx.author.name + ": " + cmd)


@client.command(brief="executes a command in minecraft")
@commands.check(lambda ctx: has_roles(ctx, LEVEL1))
async def exec(ctx, *, cmd):
    response = command('/'+cmd)
    if response != "":
        await ctx.send("```\n"+response+"\n```")


@client.command(brief="gets a list of all online players on the server")
async def online(ctx):

    response = command("/list uuids")

    users = response.split(":", 1)
    users = users[1].split(",")
    users_cleaned = []
    for u in users:
        name = ""
        for c in u[1:]:
            if c != " ":
                name += c
            else:
                break
        users_cleaned.append(name)
        print(name)
    result = "\n".join(users_cleaned)
    await ctx.send("```\n"+"\n"+result+"\n```")


@client.command(brief="vote on whitelisting a user when no mods are around 3"
                      " more positive votes are needed then negative",
                usage="!whitelist <@discord_username> <minecraft_username>")
async def whitelist(ctx: commands.Context, dis_user: discord.User, user: str):
    cursor = db.cursor("")
    sql = ("INSERT INTO requests(message_id,minecraft_username,discord_id)",
           "VALUES(?,?,?)")
    message = await ctx.send("vote on whitelisting of:\n" + user)
    cursor.execute(sql, (message.id, user, dis_user.id))
    await message.add_reaction("✅")
    await message.add_reaction("❌")
    cursor.close()


@client.command(brief="finds who a minecraft user is in discord",
                usage="!whois <minecraft_username>")
async def whois(ctx: commands.Context, user: str):
    ch: discord.TextChannel = ctx.channel()
    try:
        player = GetPlayerData(user)
    except (Exception):
        await ch.send("Error invalid Username " + user)
        return
    
    cursor = db.cursor("")
    cursor.execute(f"SELECT * FROM users WHERE minecraft_uuid = ?",
                   (player.uuid))
    rows = cursor.fetchall()
    cursor.close()
    if rows:
        disc_user: discord.User = client.get_user(int(rows[0]["discord_id"]))
        await ch.send(user + " is " + disc_user.mention)
    else:
        await ch.send(user + " isn't whitelisted on this server")


@client.event
async def on_raw_reaction_add(payload):
    guild = client.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)
    message: discord.Message = await channel.fetch_message(payload.message_id)

    if message.author.bot:  # Verify message was sent by a bot
        cursor = db.cursor("")
        cursor.execute(f"SELECT * FROM requests WHERE message_id = ?",
                       (message.id))
        rows = cursor.fetchall()
        cursor.close()
        if rows:
            vote = 0
            for r in message.reactions:
                r: discord.Reaction
                if r.emoji == "✅":
                    ids = []
                    for u in r.users:
                        ids.append(u.id)
                        for role in u.roles:
                            if role.name in LEVEL1+LEVEL2:
                                vote += 100

                    vote += len(validated_users(ids))
                    print(str(r.count)+" for")
                if r.emoji == "❌":
                    ids = []
                    for u in r.users:
                        ids.append(u.id)
                        for role in u.roles:
                            if role.name in LEVEL1+LEVEL2:
                                vote += 100
                    vote -= len(validated_users(ids))
                    print(str(r.count)+" against")

            if vote >= 3:
                username = rows[0]["minecraft_username"]
                disc_user: discord.User = client.get_user(
                    int(rows["discord_id"]))
                add_to_whitelist(username, disc_user)
                await channel.send(content="Whitelisted " +
                                   disc_user.mention + " as " + username)
                await message.delete()


@client.event
async def on_ready():
    # with open('bot.pid', 'w') as pid_file:
    #    pid_file.write(str(os.getpid()))
    print("Bot is ready")


# Start bot
client.run(DISCORDTOKEN)
