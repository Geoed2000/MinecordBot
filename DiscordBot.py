from discord.ext import commands
import subprocess
from mcrcon import MCRcon

PASSWORD: str
DISCORDTOKEN: str
SERVERADDRESS: str
LEVEL1: list
LEVEL2: list


client = commands.Bot(command_prefix="!")


def load():
    data = {}
    with open("vars.env", "r") as f:
        for line in f:
            if not(line[0] == "#" or line == ""):
                line = line.split("=")
                if len(line) != 2:
                    continue
                data[line[0].upper()] = line[1][:-1]()
    return data


def bash(bash_command: str):
    """runs bash command on the current system
    """
    # not used for now but can be useful if the bot is running on the same
    # system as the server. sucha as seeing ram usage ect
    bash_command = "monit status"

    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    output = output.decode('ascii')


def command(cmd: str):
    with MCRcon(SERVERADDRESS, PASSWORD) as mcr:
        response = mcr.command(cmd)
    return response


def has_roles(ctx, roles: list):
    for r in ctx.user.roles:
        if r.name in roles:
            return True
    return False


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
#    for i in output.decode('ascii').split("\n"):
#        if i:
#            await ctx.send(i)


@client.command(brief ="sends a message in the minecraft chat")
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
                usage="!whitelist <minecraft_username>")
async def whitelist(ctx, user: str):
    message = await ctx.send("vote on whitelisting of:\n" + user)
    await message.add_reaction("✅")
    await message.add_reaction("❌")


@client.event
async def on_raw_reaction_add(payload):

    guild = client.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    if message.author.bot:  # Verify message was sent by a bot
        if message.content.startswith("vote on whitelisting of:"):
            vote = 0
            for r in message.reactions:
                if r.emoji == "✅":
                    vote += r.count
                    print(str(r.count)+" for")
                if r.emoji == "❌":
                    vote -= r.count
                    print(str(r.count)+" against")

            if vote >= 3:
                username = message.content.split("\n")[1]
                await channel.send("Whitelisting...")
                await message.edit(content="Whitelisted user " + username)


@client.event
async def on_ready():
    # with open('bot.pid', 'w') as pid_file:
    #    pid_file.write(str(os.getpid()))
    print("Bot is ready")


data = load()
# Load vars
PASSWORD = data["PASSWORD"]
DISCORDTOKEN = data["TOKEN"]
SERVERADDRESS = data["SERVERADDRESS"]
LEVEL1 = data["LEVEL1"].split(",")
LEVEL2 = data["LEVEL2"].split(",")

# Start bot
client.run(DISCORDTOKEN)
