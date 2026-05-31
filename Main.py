import discord
from discord.ext import commands
import logging
import json
import os

TOKEN = '(DISCORD_TOKEN)'

DATA_FILE = 'data.json'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot_logs.txt"), logging.StreamHandler()]
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help') 

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f: 
            return json.load(f)
    return {"users": {}, "channels": {}}

data = load_data()

def save_data():
    with open(DATA_FILE, 'w') as f: 
        json.dump(data, f, indent=4)

shop_items = [
    ["Bread Tiki", "🍞", 30, 1],
    ["Speed Cookie Tiki", "⚡", 80, 2],
    ["Fire Snack Tiki", "🔥", 150, 3],
    ["Lucky Candy Tiki", "🍀", 300, 4],
    ["Energy Drink Tiki", "🥤", 500, 5],
    ["Cocoa Bite Tiki", "🍫", 800, 6],
    ["Crunch Roll Tiki", "🥨", 1200, 8],
    ["Gold Taco Tiki", "🌮", 2500, 15],
    ["Burger Tiki", "🍔", 7500, 30]
]

class ShopPaginationView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == len(self.embeds) - 1)

    async def update_view(self, interaction: discord.Interaction):
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        await self.update_view(interaction)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        await self.update_view(interaction)
        
@bot.check
async def check_channel(ctx):
    guild_id = str(ctx.guild.id)
    
    if ctx.command.name == "tikisetup":
        return True
       
        allowed_channel_id = data["channels"][guild_id]
        return ctx.channel.id == allowed_channel_id   
    return True

@bot.event
async def on_ready():
    logging.info(f"Bot Online: {bot.user.name}")
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Game("playing discord.py"))

@bot.event
async def on_message(message):
    if message.author.bot: 
        return
    
    guild_id = str(message.guild.id)
    
    if guild_id in data["channels"] and message.channel.id == data["channels"][guild_id]:
        content = message.content.lower()
        if "tikitiki" in content or "tiki tiki" in content:
            uid = str(message.author.id)
            user = data["users"].setdefault(uid, {"points": 0, "multiplier": 1, "inventory": []})
            
            gained = 1 * user.get("multiplier", 1)
            user["points"] += gained
            save_data()
            
            await message.add_reaction("🎵")
            logging.info(f"{message.author.name} earned {gained} points via text reaction.")

    await bot.process_commands(message)

@bot.event
async def on_command_completion(ctx):
    logging.info(f"Command executed successfully: '{ctx.command}' by {ctx.author}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command! (Requires Administrator)")
    elif isinstance(error, commands.CheckFailure):
        
        pass
    elif isinstance(error, commands.CommandNotFound):
        pass 
    else:
        logging.error(f"Error in {ctx.command}: {error}")

@bot.command()
@commands.has_permissions(administrator=True)
async def tikisetup(ctx, channel: discord.TextChannel = None):
   
    target_channel = channel or ctx.channel
    
    data["channels"][str(ctx.guild.id)] = target_channel.id
    save_data()
    
    await ctx.send(f"✅ Success! **{target_channel.mention}** is now configured as the exclusive Tiki Tiki channel. All other channels are locked out.")
    logging.info(f"Tiki channel changed to {target_channel.name} in guild {ctx.guild.name}")

@bot.command()
async def tikihelp(ctx):
    embed = discord.Embed(title="📜 Tiki Tiki Bot — All Commands Sheet", color=discord.Color.teal())
    embed.add_field(name="🛠️ Configuration", value="`!tikisetup [#channel]` — Changes the designated bot channel. (Admin Only)", inline=False)
    embed.add_field(name="📊 Economy & Stats", value="`!tikipoints [user]` — Views total points.\n`!tikiowned [user]` — Views your items.\n`!tikitop` — Views the Top 10 Leaderboard.\n`!tikisend <user> <amount>` — Send points.", inline=False)
    embed.add_field(name="🛒 Shop", value="`!tikishop` — Opens shop layers.\n`!tikibuy <item name>` — Buys an item.", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def tikishop(ctx):
    items_per_page = 3
    pages = [shop_items[i:i + items_per_page] for i in range(0, len(shop_items), items_per_page)]
    
    embeds = []
    for i, page_items in enumerate(pages):
        embed = discord.Embed(title="🛒 Tiki Tiki Shop", color=discord.Color.blue())
        for item in page_items:
            name, emoji, price, mult = item
            embed.add_field(name=f"{emoji} {name}", value=f"💰 Price: {price}\n⚡ Multiplier: x{mult}", inline=False)
        embed.set_footer(text=f"Page {i+1} / {len(pages)}")
        embeds.append(embed)
    await ctx.send(embed=embeds[0], view=ShopPaginationView(embeds))

@bot.command()
async def tikibuy(ctx, *, item_name: str):
    found_item = next((item for item in shop_items if item_name.lower() in item[0].lower()), None)
    if not found_item: 
        return await ctx.send("❌ Item not found! Use `!tikishop` to see accurate spelling.")
    
    name, emoji, price, mult = found_item
    uid = str(ctx.author.id)
    user = data["users"].setdefault(uid, {"points": 0, "multiplier": 1, "inventory": []})
    
    if "inventory" not in user: user["inventory"] = []
    if name in user["inventory"]: return await ctx.send(f"❌ You already own **{emoji} {name}**!")
    
    if user["points"] >= price:
        user["points"] -= price
        user["multiplier"] = mult
        user["inventory"].append(name)
        save_data()
        await ctx.send(f"✅ Purchased **{emoji} {name}**! New multiplier: **x{mult}**.")
    else:
        await ctx.send(f"❌ Insufficient points. You need {price} points.")

@bot.command()
async def tikiowned(ctx, member: discord.Member = None):
    member = member or ctx.author
    uid = str(member.id)
    user_profile = data["users"].get(uid, {"points": 0, "multiplier": 1, "inventory": []})
    inventory = user_profile.get("inventory", [])
    
    embed = discord.Embed(title=f"🎒 {member.name}'s Tiki Tiki Inventory", color=discord.Color.dark_green())
    if not inventory:
        embed.description = "Inventory is empty!"
    else:
        lines = []
        for i in inventory:
            m = next((item for item in shop_items if item[0].lower() == i.lower()), None)
            lines.append(f"{m[1] if m else '📦'} **{i}**")
        embed.description = "\n".join(lines)
    await ctx.send(embed=embed)

@bot.command()
async def tikipoints(ctx, member: discord.Member = None):
    member = member or ctx.author
    u = data["users"].get(str(member.id), {"points": 0, "multiplier": 1})
    embed = discord.Embed(title=f"📊 {member.name}'s Tiki Tiki Stats", color=discord.Color.green())
    embed.add_field(name="Total Points", value=str(u.get("points", 0)), inline=True)
    embed.add_field(name="Current Multiplier", value=f"x{u.get('multiplier', 1)}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def tikisend(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("❌ Amount must be positive.")
    sender, receiver = str(ctx.author.id), str(member.id)
    if data["users"].get(sender, {}).get("points", 0) >= amount:
        data["users"][sender]["points"] -= amount
        rec = data["users"].setdefault(receiver, {"points": 0, "multiplier": 1, "inventory": []})
        rec["points"] += amount
        save_data()
        await ctx.send(f"💸 ✅ Successfully sent **{amount}** points to **{member.name}**!")
    else:
        await ctx.send("❌ You do not have enough points.")

@bot.command()
async def tikitop(ctx):
    sorted_users = sorted(data["users"].items(), key=lambda x: x[1]['points'], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Top 10 Tiki Tiki Players", color=discord.Color.gold())
    lines = [f"**{i}.** {ctx.guild.get_member(int(uid)).name if ctx.guild.get_member(int(uid)) else 'Unknown User'} Tiki Tiki — **{udata['points']} pts**" for i, (uid, udata) in enumerate(sorted_users, 1)]
    embed.description = "\n\n".join(lines) if lines else "No data yet."
    await ctx.send(embed=embed)
    
@bot.command()
async def tikiinfo(ctx):
    
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="ℹ️ Tiki Tiki Bot — Official Information Dashboard",
        description="Welcome to the core database of the Tiki Tiki system. Here you can find our build metrics, developer team, and legal frameworks.",
        color=discord.Color.purple()
    )
    
    
    embed.add_field(
        name="⚙️ System Specifications",
        value=(
            f"**• Engine Language:** Python 3.13\n"
            f"**• Library API:** `discord.py`\n"
            f"**• Command Prefix:** `{bot.command_prefix}`\n"
            f"**• Connection Ping:** `{latency}ms`"
        ),
        inline=True
    )
    
    # Development Team Field
    embed.add_field(
        name="👥 Development Roster",
        value=(
            "**• Project Lead:** `@itzzlr`\n"
            "**• System Architect:** `@__defnotaya`\n"
            "**• Status:** Active Production"
        ),
        inline=True
    )
    
    # System Command Index
    embed.add_field(
        name="📜 Complete Command Directory",
        value=(
            "`!tikihelp` — Explains command mechanics & structures.\n"
            "`!tikiinfo` — Opens this technical specifications directory.\n"
            "`!tikisetup [#channel]` — Locks bot execution to a channel. *(Admin)*\n"
            "`!tikishop` — Opens the 3-page interactive multiplier marketplace.\n"
            "`!tikibuy <item>` — Purchases a passive multiplier asset.\n"
            "`!tikiowned [user]` — Audits item ownership logs.\n"
            "`!tikipoints [user]` — Requests live wallet point ledger balances.\n"
            "`!tikisend <user> <amount>` — Facilitates secure point transfers.\n"
            "`!tikitop` — Fetches global server point leaderboard."
        ),
        inline=False
    )
    
    
    embed.add_field(
        name="⚖️ Legal & Compliance",
        value=(
            "**• Terms of Service:** NONE / [Review Document](https://google.com)\n"
            "**• Privacy Policy:** NONE / [Review Document](https://google.com)"
        ),
        inline=False
    )
    
    embed.set_footer(text="Tiki Tiki System • Empowering text chat economies.")
    
    await ctx.send(embed=embed)

bot.run(TOKEN)
