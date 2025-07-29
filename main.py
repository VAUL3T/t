import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import random
import os
import json
import typing
import time
import asyncio
from discord import app_commands
from discord.ext.commands import has_permissions, MissingPermissions
from datetime import datetime, timedelta
from discord.ext.commands import CheckFailure

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Nur ein Server → feste Datei
WHITELISTED_GUILDS = [1345476135487672350]
DATA_FILE = "1345476135487672350.json"
bot = commands.Bot(command_prefix='beach ', help_command=None, intents=intents)
tree = bot.tree
PET_FILE = "1345476135487672350.json"
PET_ACTION_COOLDOWN = 300  # 5 Min
WORK_COOLDOWN = 1800     
user_balances = {}
user_last_lottery = {}
lottery_data = {}
last_pray_time = {}
lottery_active = False
robbery_cooldowns = {}
work_cooldowns = {}
minesweeper_cooldowns = {}
user_luck = {}
START_LIVES = 3
esex_cooldowns = {}
START_BALANCE = 100000
MIN_BET = 5
crime_cooldowns = {}
payment_lock_until = {}

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print("synced cmd")
    decay_pet_stats.start()

@bot.check
async def globally_whitelist_guilds(ctx):
    if ctx.guild is None:
        return False  # Ignoriere DMs
    return ctx.guild.id in WHITELISTED_GUILDS

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"users": {}, "server": {}}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def is_admin(interaction: discord.Interaction):
    return interaction.user.guild_permissions.administrator
    

def get_balance(user_id):
    data = load_data()
    user = data["users"].setdefault(str(user_id), {})

    if "balance" not in user:
        user["balance"] = START_BALANCE
        save_data(data)

    return user["balance"]

def update_balance(user_id, amount):
    data = load_data()
    user = data["users"].setdefault(str(user_id), {})
    user["balance"] = user.get("balance", 0) + amount
    save_data(data)

def get_luck_bonus(user_id):
    data = load_data()
    luck = data["users"].get(str(user_id), {}).get("luck", 0)
    data["users"][str(user_id)]["luck"] = 0  # zurücksetzen
    save_data(data)
    return luck

def set_luck(user_id, value):
    data = load_data()
    user = data["users"].setdefault(str(user_id), {})
    user["luck"] = value
    save_data(data)

def get_server_setting(key, default):
    data = load_data()
    return data["server"].get(key, default)

def set_server_setting(key, value):
    data = load_data()
    data["server"][key] = value
    save_data(data)

def get_pet_data(user_id):
    data = load_data()
    return data["users"].get(str(user_id), {}).get("pet")

def set_pet_data(user_id, pet_data):
    data = load_data()
    data["users"].setdefault(str(user_id), {})["pet"] = pet_data
    save_data(data)

def pet_progress_bar(value):
    blocks = int(value / 10)
    return f"{'█'*blocks}{'░'*(10-blocks)} {value}/100"

def get_pet_emoji(pet_type):
    return {"Dog": "🐶", "Cat": "🐱", "Rabbit": "🐰", "Hamster": "🐹"}.get(pet_type, "🐾")

def get_earn_amount(hunger, happy, clean):
    if min(hunger, happy, clean) > 90:
        return random.randint(15000, 25000)
    elif min(hunger, happy, clean) > 80:
        return random.randint(5000, 15000)
    elif min(hunger, happy, clean) > 40:
        return random.randint(3000, 5000)
    return 1000

def get_age_hours(pet):
    created = datetime.fromtimestamp(pet["created"])
    return int((datetime.utcnow() - created).total_seconds() // 3600)

last_pet_actions = {}

@tree.command(name="clear_cooldowns", description="👑[ADMIN] Clear all cooldowns")
@app_commands.check(is_admin)
async def clear_cooldowns(interaction: discord.Interaction):
    global last_pray_time, robbery_cooldowns, work_cooldowns
    global minesweeper_cooldowns, esex_cooldowns, crime_cooldowns, payment_lock_until

    last_pray_time.clear()
    robbery_cooldowns.clear()
    work_cooldowns.clear()
    minesweeper_cooldowns.clear()
    esex_cooldowns.clear()
    crime_cooldowns.clear()
    payment_lock_until.clear()

    embed = discord.Embed(
        description="🟢 All cooldowns have been cleared successfully.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="reset-econemy", description="👑[ADMIN] Reset player balances")
@app_commands.check(is_admin)
async def reset_econemy(interaction: discord.Interaction):
    file_path = f"{interaction.guild.id}.json"

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    data["users"] = {}  # Alle User-Daten löschen

    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

    embed = discord.Embed(
        description="🟢 Economy wurde erfolgreich zurückgesetzt.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)
    
@tree.command(name="set-start-money", description="👑[ADMIN] Set starting balance (10k - 1m)")
@app_commands.describe(value="New starting balance (10000 - 1000000)")
@app_commands.check(is_admin)
async def set_start_money(interaction: discord.Interaction, value: int):
    global START_BALANCE
    if 10000 <= value <= 1_000_000:
        START_BALANCE = value
        embed = discord.Embed(
            description=f"🟢 START_BALANCE set to **${START_BALANCE:,}**",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            description="🔴 Value must be between 10,000 and 1,000,000",
            color=discord.Color.red()
        )
    await interaction.response.send_message(embed=embed)

@bot.command(name="help")
async def beach_help(ctx):
    # Dein embed code hier
    embed = discord.Embed(
        title="🎮 **Beach : Available Games**",
        description="Browse and play any of the available games and test your luck",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🎲 Classic Casino Games",
        value=(
            "> 🎡 Roulette : `roulette`\n"
            "> Alias : rl\n"
            "> Usage : roulette <bet>\n"

            "> 🎰 Slots : `slots`\n"
            "> Alias : sl\n"
            "> Usage : slots <bet>\n"

            "> 🪙 Coinflip : `coinflip`\n"
            "> Alias : cf\n"
            "> Usage : coinflip <bet>\n"

            "> 💣 Minesweeper : `minesweeper`\n"
            "> Alias : ms\n"
            "> Usage : minesweeper\n"

            "> 🎲 Roulette: `roulette`\n"
            "> Alias : re\n"
            "> Usage : roulette <bet>"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 Adventure & Fun",
        value=(
            "> 🥷 Crime : `crime`\n"
            "> Usage : crime\n"

            "> 🐾 Pets : `/pets`\n"

            "> 💕 Esex : `esex`\n"
            "> Usage : esex | esex <@user>\n"

            "> 🥺 Beg : `beg`\n"
            "> Usage : beg\n"

            "> 👷‍♂️ Work : `work`\n"
            "> Usage : work"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Utility’s",
        value=(
            "> 💸 Balance : `balance`\n"
            "> Alias : bal\n"
            "> Usage : balance\n"

            "> 🙏 Pray : `pray`\n"
            "> Usage : pray\n"

            "> 💵 Pay : `pay`\n"
            "> Usage : pay <@user> <money>"
        ),
        inline=False
    )

    await ctx.send(embed=embed)
    
@bot.command(aliases=["ms"])
async def minesweeper(ctx):
    user_id = ctx.author.id
    now = time.time()

    # Cooldown 5 Minuten
    last = minesweeper_cooldowns.get(user_id, 0)
    if now - last < 5:
        remain = int(5 - (now - last))
        minutes, seconds = divmod(remain, 60)
        return await ctx.send(embed=discord.Embed(
            description=f"🕒 You must wait **{minutes}m {seconds}s** before playing again.",
            color=discord.Color.red()
        ))

    luck = user_luck.pop(user_id, 0)

    width, height = 5, 4
    total_fields = width * height

    bombs_count = max(1, 6 - (luck // 5))
    bomb_positions = set(random.sample(range(total_fields), bombs_count))

    async def reveal_all_buttons(view, bomb_positions):
        for child in view.children:
            if isinstance(child, Button):
                child.disabled = True
                if child.idx in bomb_positions:
                    child.label = "💣"
                    child.style = discord.ButtonStyle.danger
                else:
                    child.label = "🟢"
                    child.style = discord.ButtonStyle.success

    class MSButton(Button):
        def __init__(self, idx):
            super().__init__(style=discord.ButtonStyle.secondary, label="?")
            self.idx = idx

        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != user_id:
                await interaction.response.send_message("🔴 This isn’t your game", ephemeral=True)
                return

            if self.disabled:
                await interaction.response.defer()
                return

            lives = self.view.lives
            safe_found = self.view.safe_found
            money_won = self.view.money_won

            if self.idx in bomb_positions:
                lives -= 1
                self.view.lives = lives
                self.label = "💣"
                self.style = discord.ButtonStyle.danger
                self.disabled = True
            else:
                safe_found += 1
                self.view.safe_found = safe_found
                self.label = "🟢"
                self.style = discord.ButtonStyle.success
                self.disabled = True
                money_won += 500
                self.view.money_won = money_won

            for child in self.view.children:
                if isinstance(child, Button):
                    if child.idx in bomb_positions and child.disabled:
                        child.label = "💣"
                        child.style = discord.ButtonStyle.danger
                    elif child.disabled:
                        child.label = "🟢"
                        child.style = discord.ButtonStyle.success

            embed = discord.Embed(
                title="💣 **Game summary**",
                description=(
                    f"> Safe tiles found : {safe_found}\n"
                    f"> Money won       : ${money_won}\n"
                    f"> Player          : {ctx.author.mention}\n"
                    f"> Life's left     : {lives}\n\n"
                    f"💡Quick Tip\nGet more luck using - **beach pray**"
                ),
                color=discord.Color.gold()
            )

            if lives <= 0:
                embed.title = "💥 **Game lost**"
                await reveal_all_buttons(self.view, bomb_positions)
                minesweeper_cooldowns[user_id] = time.time()
                update_balance(user_id, self.view.money_won)
                await interaction.response.edit_message(embed=embed, view=self.view)
                return

            safe_tiles_needed = total_fields - bombs_count
            if safe_found == safe_tiles_needed:
                embed.title = "💣 **Game won**"
                self.view.money_won = 60000
                embed.description = (
                    f"> Safe tiles found : {safe_found}\n"
                    f"> Money won       : $60000\n"
                    f"> Player          : {ctx.author.mention}\n"
                    f"> Life's left     : {lives}\n\n"
                    f"💡Quick Tip\nGet more luck using - **beach pray**"
                )
                await reveal_all_buttons(self.view, bomb_positions)
                minesweeper_cooldowns[user_id] = time.time()
                update_balance(user_id, self.view.money_won)
                await interaction.response.edit_message(embed=embed, view=self.view)
                return

            await interaction.response.edit_message(embed=embed, view=self.view)

    class MSView(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.lives = START_LIVES
            self.safe_found = 0
            self.money_won = 0
            for i in range(total_fields):
                self.add_item(MSButton(i))

    view = MSView()

    embed = discord.Embed(
        title="💣 **Game summary**",
        description=(
            f"> Safe tiles found : 0\n"
            f"> Money won       : $0\n"
            f"> Player          : {ctx.author.mention}\n"
            f"> Life's left     : {START_LIVES}\n\n"
            f"💡Quick Tip\nGet more luck using - **beach pray**"
        ),
        color=discord.Color.gold()
    )

    await ctx.send(embed=embed, view=view)
    
@bot.command(aliases=['cf'])
async def coinflip(ctx, bet: int):
    user_id = ctx.author.id

    if bet < MIN_BET:
        embed = discord.Embed(
            description=f"🔴 Your bet must be at least **${MIN_BET}**",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if get_balance(user_id) < bet:
        embed = discord.Embed(
            description="🔴 You don’t have enough money",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    luck_bonus = get_luck_bonus(user_id)
    total_chance = 50 + luck_bonus

    embed = discord.Embed(
        description=f"Select a option: Head/Tails\nYour bet **${bet}**\n\n💡 Quick tip\nGet more luck using - **beach pray**",
        color=discord.Color.gold()
    )

    class CoinFlipView(View):
        def __init__(self):
            super().__init__(timeout=30)

        @discord.ui.button(label="🪙 Head", style=discord.ButtonStyle.primary)
        async def head(self, interaction: discord.Interaction, button: Button):
            await self.resolve(interaction, "Head")

        @discord.ui.button(label="🪙 Tails", style=discord.ButtonStyle.primary)
        async def tails(self, interaction: discord.Interaction, button: Button):
            await self.resolve(interaction, "Tails")

        async def resolve(self, interaction, choice):
            result = random.choice(["Head", "Tails"])
            roll = random.uniform(0, 100)
            win = choice == result and roll <= total_chance

            if win:
                update_balance(user_id, bet)
                result_embed = discord.Embed(
                    description=f"You flipped the coin and it landed on **{result}**\nYou won **${bet * 2}**\n\n💡 Quick tip\nGet more luck using - **beach pray**",
                    color=discord.Color.green()
                )
            else:
                update_balance(user_id, -bet)
                result_embed = discord.Embed(
                    description=f"You flipped the coin and it landed on **{result}**\nYou lose **${bet}**\n\n💡 Quick tip\nGet more luck using - **beach pray**",
                    color=discord.Color.red()
                )

            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=result_embed, view=self)

    await ctx.send(embed=embed, view=CoinFlipView())

@bot.command()
async def beg(ctx):
    user_id = ctx.author.id

    # Hole Luck & verbrauche es (einmalig)
    luck = user_luck.pop(user_id, 0)

    # Basisverteilung
    low = list(range(100, 501)) * 40
    mid = list(range(501, 1001)) * 25
    high = list(range(1001, 2001)) * 15
    very_high = list(range(2001, 5001)) * 5

    # Luck beeinflusst die Gewichtung:
    # Je mehr Luck, desto mehr high/very_high wird reingemischt
    weighted_amounts = (
        low +
        mid +
        high * (1 + luck // 20) +
        very_high * (1 + luck // 10)
    )

    earned = random.choice(weighted_amounts)
    previous = get_balance(user_id)
    update_balance(user_id, earned)
    current = get_balance(user_id)

    embed = discord.Embed(
        title=f"🎭 Your street performance earned you **${earned}**",
        description=(
            f"💰 **Balance Update**\n"
            f"> Previous : ${previous}\n"
            f"> Earned   : ${earned}\n"
            f"> Current  : ${current}\n\n"
            f"💡 Quick Tip\n"
            f"Get more luck using - **beach pray**"
        ),
        color=discord.Color.orange()
    )

    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)

    await ctx.send(embed=embed)

class PetView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    @discord.ui.button(label="🍔 Feed", style=discord.ButtonStyle.green)
    async def feed(self, interaction, button):
        now = datetime.utcnow().timestamp()
        if now - last_pet_actions.get((self.user_id, "feed"), 0) < PET_ACTION_COOLDOWN:
            remain = int(PET_ACTION_COOLDOWN - (now - last_pet_actions[(self.user_id, "feed")]))
            m, s = divmod(remain, 60)
            return await interaction.response.send_message(f"🕒 You must wait **{m:02}m {s:02}s** before using this command again", ephemeral=True)
        pet = get_pet_data(self.user_id)
        if not pet: return
        pet["hunger"] = min(pet["hunger"] + 20, 100)
        last_pet_actions[(self.user_id, "feed")] = now
        set_pet_data(self.user_id, pet)
        await interaction.response.edit_message(embed=make_pet_embed(self.user_id), view=self)

    @discord.ui.button(label="🛝 Play", style=discord.ButtonStyle.blurple)
    async def play(self, interaction, button):
        now = datetime.utcnow().timestamp()
        if now - last_pet_actions.get((self.user_id, "play"), 0) < PET_ACTION_COOLDOWN:
            remain = int(PET_ACTION_COOLDOWN - (now - last_pet_actions[(self.user_id, "play")]))
            m, s = divmod(remain, 60)
            return await interaction.response.send_message(f"🕒 You must wait **{m:02}m {s:02}s** before using this command again", ephemeral=True)
        pet = get_pet_data(self.user_id)
        if not pet: return
        pet["happiness"] = min(pet["happiness"] + 20, 100)
        pet["hunger"] = max(pet["hunger"] - 10, 0)
        last_pet_actions[(self.user_id, "play")] = now
        set_pet_data(self.user_id, pet)
        await interaction.response.edit_message(embed=make_pet_embed(self.user_id), view=self)

    @discord.ui.button(label="💦 Clean", style=discord.ButtonStyle.gray)
    async def clean(self, interaction, button):
        now = datetime.utcnow().timestamp()
        if now - last_pet_actions.get((self.user_id, "clean"), 0) < PET_ACTION_COOLDOWN:
            remain = int(PET_ACTION_COOLDOWN - (now - last_pet_actions[(self.user_id, "clean")]))
            m, s = divmod(remain, 60)
            return await interaction.response.send_message(f"🕒 You must wait **{m:02}m {s:02}s** before using this command again", ephemeral=True)
        pet = get_pet_data(self.user_id)
        if not pet: return
        pet["clean"] = min(pet["clean"] + 25, 100)
        last_pet_actions[(self.user_id, "clean")] = now
        set_pet_data(self.user_id, pet)
        await interaction.response.edit_message(embed=make_pet_embed(self.user_id), view=self)

    @discord.ui.button(label="💪 Work", style=discord.ButtonStyle.red)
    async def work(self, interaction, button):
        now = datetime.utcnow().timestamp()
        if now - last_pet_actions.get((self.user_id, "work"), 0) < WORK_COOLDOWN:
            remain = int(WORK_COOLDOWN - (now - last_pet_actions[(self.user_id, "work")]))
            m, s = divmod(remain, 60)
            return await interaction.response.send_message(f"🕒 You must wait **{m:02}m {s:02}s** before using this command again", ephemeral=True)
        pet = get_pet_data(self.user_id)
        if not pet: return
        earned = get_earn_amount(pet["hunger"], pet["happiness"], pet["clean"])
        update_balance(self.user_id, earned)
        pet["clean"] = max(pet["clean"] - 15, 0)
        pet["happiness"] = max(pet["happiness"] - 15, 0)
        pet["earned"] += earned
        pet["level"] += 1
        last_pet_actions[(self.user_id, "work")] = now
        set_pet_data(self.user_id, pet)
        await interaction.response.edit_message(embed=make_pet_embed(self.user_id), view=self)

    @discord.ui.button(label="⚙️ Change Pet ", style=discord.ButtonStyle.red)
    async def settings(self, interaction, button):
        pet = get_pet_data(self.user_id)
        if not pet:
            return await interaction.response.send_message("You have no pet to manage.", ephemeral=True)
        embed = discord.Embed(
            title="Are you sure you want to delete your pet?",
            description=(
                "**This will delete:**\n"
                "• All pet stats and progress\n"
                f"• Level {pet.get('level', 1)}\n\n"
                "After deletion, you can adopt a new pet.\n"
                "You lose **$1000**"
            ),
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=ConfirmDeletePetView(self.user_id), ephemeral=True)

class ConfirmDeletePetView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.red)
    async def confirm(self, interaction, button):
        data = load_data()
        user_data = data["users"].get(str(self.user_id), {})
        balance = user_data.get("balance", 0)

        if balance < 1000:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description="🔴 You don’t have enough money",
                    color=discord.Color.red()
                ),
                view=None
            )
            return

        # 1000$ abziehen und pet löschen
        user_data["balance"] -= 1000
        user_data.pop("pet", None)
        save_data(data)

        await interaction.response.edit_message(
            embed=discord.Embed(
                description="🟢 Your pet has been deleted. You can now adopt a new one.",
                color=discord.Color.green()
            ),
            view=None
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction, button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        
def make_pet_embed(user_id):
    pet = get_pet_data(user_id)
    if not pet:
        return discord.Embed(description="No pet found.", color=discord.Color.red())

    age = get_age_hours(pet)
    emoji = get_pet_emoji(pet["type"])
    embed = discord.Embed(
        title=f"{emoji} {pet['type']}",
        description=(
            f"> Level : {pet['level']}\n"
            f"> Age   : {age}h\n\n"
            f"🍔 Hunger :\n{pet_progress_bar(pet['hunger'])}\n\n"
            f"🛝 Happiness :\n{pet_progress_bar(pet['happiness'])}\n\n"
            f"💦 Cleanliness :\n{pet_progress_bar(pet['clean'])}\n\n"
            f"💰 Total earned :\n**${pet['earned']}**"
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="💰Keep all stats above 80 for ENHANCED EARNINGS")
    return embed

class PetSelect(Select):
    def __init__(self, user_id):
        options = [discord.SelectOption(label=pet, emoji=get_pet_emoji(pet)) for pet in ["Dog", "Cat", "Rabbit", "Hamster"]]
        super().__init__(placeholder="🐾 Select your pet type", options=options)
        self.user_id = user_id

    async def callback(self, interaction):
        selected = self.values[0]
        pet_data = {
            "type": selected,
            "level": 1,
            "hunger": 50,
            "happiness": 50,
            "clean": 50,
            "earned": 0,
            "created": datetime.utcnow().timestamp()
        }
        set_pet_data(self.user_id, pet_data)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"You’ve adopted a wonderful {selected}",
                description="🍔 Feed your pet to keep them healthy\n🛝 Play with them to keep them happy\n💦 Clean them regularly\n💪 Work with them to earn money",
                color=discord.Color.green()
            ), view=None)

class PetSelectView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.add_item(PetSelect(user_id))

@bot.tree.command(name="pet", description="🐾 Manage or view your pets")
@app_commands.describe(user="View another user's pet")
async def pet(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    user_id = target_user.id
    pet = get_pet_data(user_id)

    if not pet:
        if user and user.id != interaction.user.id:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{user.mention} has no pet.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
        # Du selbst hast kein Pet → Auswahl anzeigen
        embed = discord.Embed(
            title="🐾 Welcome to Pet Paradise",
            description=(
                "> You don’t have a pet yet!\n> Choose one below to get started\n\n"
                "🎯 How it works:\n"
                "🍔 Feed your pet to keep them healthy\n"
                "🛝 Play with them to keep them happy\n"
                "💦 Clean them regularly\n"
                "💪 Work with them to earn money\n\n"
                "> ⚠️ Pet dies after 2 days without care"
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="well-cared pets can earn you serious money")
        return await interaction.response.send_message(embed=embed, view=PetSelectView(interaction.user.id))

    # Pet existiert
    embed = make_pet_embed(user_id)
    
    # Wenn anderer User angegeben ist → Embed ohne Buttons + Footer
    if user and user.id != interaction.user.id:
        embed.set_footer(text=f"👀 Viewing {user.mention}’s pet | Use /pet to adopt your own companion")
        return await interaction.response.send_message(embed=embed)

    # Ansonsten: eigenes Pet → Embed mit Buttons
    await interaction.response.send_message(embed=embed, view=PetView(user_id))
    
@bot.command(aliases=["sl"])
async def slots(ctx, bet: int):
    user_id = ctx.author.id

    if bet < MIN_BET:
        embed = discord.Embed(
            description=f"🔴 Your bet must be at least **${MIN_BET}**",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if get_balance(user_id) < bet:
        embed = discord.Embed(
            description="🔴 You don’t have enough money",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    symbols = ["🟢", "🔴", "⚫️"]
    luck = user_luck.get(user_id, 0)
    user_luck[user_id] = 0  # ❗️Luck reset nach Spiel

    # Gewinnchance basierend auf Luck
    base_chance = 0.04
    bonus_per_luck = 0.006
    win_chance = base_chance + (bonus_per_luck * luck)

    is_win = random.random() < win_chance

    if is_win:
        symbol = random.choice(symbols)
        slot_result = [symbol] * 3
        win_amount = bet * 2
        update_balance(user_id, win_amount)
        result_title = f"🎰 **Slot Results** - WON - **${win_amount}**"
        color = discord.Color.green()
        new_balance = get_balance(user_id)
        previous = new_balance - win_amount
    else:
        slot_result = [random.choice(symbols) for _ in range(3)]
        update_balance(user_id, -bet)
        result_title = f"🎰 **Slot Results** - LOST - **${bet}**"
        color = discord.Color.red()
        new_balance = get_balance(user_id)
        previous = new_balance + bet

    embed = discord.Embed(
        title=result_title,
        description=(
            f"🎲 **Spin Results**\n"
            f"> {' | '.join(slot_result)}\n\n"
            f"💰**Balance Update**\n"
            f"> Previous : `${previous:,}`\n"
            f"> Current : `${new_balance:,}`\n\n"
            f"💡Quick Tip\nGet more luck using - **beach pray**"
        ),
        color=color
    )

    await ctx.send(embed=embed)

@bot.command()
async def esex(ctx, member: discord.Member = None):
    if ctx.guild is None:
        return await ctx.send("Server only.")

    user_id = ctx.author.id
    now = time.time()
    cooldown = 30 * 60  # 30 Minuten

    if user_id in esex_cooldowns:
        elapsed = now - esex_cooldowns[user_id]
        if elapsed < cooldown:
            remaining = cooldown - elapsed
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            return await ctx.send(
                embed=discord.Embed(
                    description=f"🕒 You must wait **{minutes}m {seconds}s** before using this command again.",
                    color=discord.Color.red()
                )
            )

    # Wenn kein Member angegeben, suche zufälligen Online/DND/Idle User außer Bots & dich selbst
    if member is None:
        candidates = [
            m for m in ctx.guild.members
            if m.status in (discord.Status.online, discord.Status.idle, discord.Status.dnd)
            and not m.bot and m != ctx.author
        ]
        if not candidates:
            return await ctx.send(embed=discord.Embed(description="🔴 No e-sex partner found", color=discord.Color.red()))
        partner = random.choice(candidates)
    else:
        # Member angegeben, prüfen ob Bot oder sich selbst
        if member.bot:
            return await ctx.send(embed=discord.Embed(description="🔴 You can’t e-sex bots", color=discord.Color.red()))
        if member == ctx.author:
            return await ctx.send(embed=discord.Embed(description="🔴 You can’t e-sex yourself", color=discord.Color.red()))
        partner = member

    earned = random.randint(100, 1000)

    previous = user_balances.get(user_id, START_BALANCE)
    new_balance = previous + earned
    user_balances[user_id] = new_balance

    esex_cooldowns[user_id] = now

    embed = discord.Embed(
        title=f"🎭 Your **e-sex** with **{partner.display_name}** earned you **${earned}**",
        color=discord.Color.magenta()
    )
    embed.add_field(
        name="💰 **Balance Update**",
        value=(
            f"> **Previous**: `${previous}`\n"
            f"> **Earned**: `${earned}`\n"
            f"> **Current**: `${new_balance}`"
        ),
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command()
async def work(ctx):
    user_id = ctx.author.id
    now = time.time()
    cooldown_time = 12 * 60  # 12 Minuten

    last_used = work_cooldowns.get(user_id, 0)
    time_since = now - last_used

    if time_since < cooldown_time:
        remaining = int(cooldown_time - time_since)
        minutes, seconds = divmod(remaining, 60)
        time_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

        embed = discord.Embed(
            description=f"🕒 You must wait **{time_str}** before working again",
            color=discord.Color.orange()
        )
        return await ctx.send(embed=embed)

    hours = random.randint(6, 12)
    amount = random.randint(5000, 12000)

    update_balance(user_id, amount)
    work_cooldowns[user_id] = now

    embed = discord.Embed(
        description=f"🟢 You worked for {hours}h and earned **${amount:,}**",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
async def crime(ctx):
    user_id = ctx.author.id
    now = time.time()

    # Check Crime cooldown (35 Minuten)
    last_crime = crime_cooldowns.get(user_id, 0)
    cooldown_seconds = 35 * 60
    if now - last_crime < cooldown_seconds:
        remaining = int(cooldown_seconds - (now - last_crime))
        minutes, seconds = divmod(remaining, 60)
        embed = discord.Embed(
            description=f"🕒 You must wait **{minutes}m {seconds}s** before committing another crime.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Gewinn/Verlust-Bereiche
    base_money = random.randint(13000, 15000)
    luck = user_luck.pop(user_id, 0)  # Luck einmalig nutzen & zurücksetzen

    # Erfolgschance mit Luck (40% + Luck Modifier, max 90%)
    base_chance = 0.40
    luck_modifier = luck / 100  # z.B. 50 Luck = +0.5 = max cap applies
    success_chance = min(base_chance + luck_modifier, 0.9)
    success = random.random() < success_chance

    tax_rate = 0.20  # 20% criminal tax
    tax_amount = int(base_money * tax_rate)

    if success:
        # Gewinn nach Steuer
        money_after_tax = base_money - tax_amount
        previous_balance = user_balances.get(user_id, START_BALANCE)
        new_balance = previous_balance + money_after_tax
        user_balances[user_id] = new_balance

        embed = discord.Embed(
            title="💸 You made it 💸",
            description=(
                f"**${tax_amount:,}** was collected as criminal tax.\n\n"
                f"💡Quick Tip\nGet more luck using - **beach pray**"
            ),
            color=discord.Color.green()
        )

    else:
        # Verlust: 80% vom möglichen Gewinn verlieren
        lost_money = int(base_money * 0.80)
        previous_balance = user_balances.get(user_id, START_BALANCE)
        remaining_money = previous_balance - lost_money

        # Update Balance nicht negativ werden lassen
        if remaining_money < 0:
            lost_money = previous_balance
            remaining_money = 0

        user_balances[user_id] = remaining_money

        embed = discord.Embed(
            title="🚨 Caught Red-Handed! 🚨",
            description=(
                f"You triggered an alarm and lost **${lost_money:,}** while escaping!\n"
                f"**${tax_amount:,}** was collected as criminal tax.\n\n"
                f"🔴 **1-Hour payment block activated!**\n\n"
                f"💡Quick Tip\nGet more luck using - **beach pray**"
            ),
            color=discord.Color.red()
        )

        # 1 Stunde Payment Lock setzen
        payment_lock_until[user_id] = now + 3600

    # Crime cooldown setzen
    crime_cooldowns[user_id] = now

    await ctx.send(embed=embed)

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    sender_id = ctx.author.id
    receiver_id = member.id
    now = time.time()

    # Payment Lock Check
    lock_time = payment_lock_until.get(sender_id, 0)
    if now < lock_time:
        remaining = int(lock_time - now)
        minutes, seconds = divmod(remaining, 60)
        embed = discord.Embed(
            description=f"🔴 You are currently under payment block for another **{minutes}m {seconds}s** and cannot send money.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Bots ausschließen
    if member.bot:
        embed = discord.Embed(
            description="🔴 You can’t pay bots",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Nicht an sich selbst zahlen
    if sender_id == receiver_id:
        embed = discord.Embed(
            description="🔴 You can’t pay yourself",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Mindestbetrag
    if amount < 5:
        embed = discord.Embed(
            description="🔴 You need to transfer at least **$5**",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    sender_balance = user_balances.get(sender_id, START_BALANCE)

    # Nicht genug Geld
    if sender_balance < amount:
        embed = discord.Embed(
            description="🔴 You don’t have enough money",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Überweisen
    user_balances[sender_id] = sender_balance - amount
    user_balances[receiver_id] = user_balances.get(receiver_id, START_BALANCE) + amount

    embed = discord.Embed(
        description=f"🟢 Successfully sent **${amount:,}** to {member.mention}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(aliases=["bal"])
async def balance(ctx, *, target_arg: typing.Optional[str] = None):
    target = ctx.author

    if target_arg:
        # Wenn Mention vorhanden, nimm Mention
        if ctx.message.mentions:
            target = ctx.message.mentions[0]
        else:
            # Falls nur eine User-ID gegeben ist
            if target_arg.isdigit():
                user_id = int(target_arg)
                member = ctx.guild.get_member(user_id)
                if member:
                    target = member
                else:
                    try:
                        # Fallback: User holen (auch wenn nicht im Server sichtbar)
                        user = await bot.fetch_user(user_id)
                        target = user
                    except:
                        pass 

            if isinstance(target, discord.User) and target == ctx.author:
                lower_arg = target_arg.lower()
                matched = discord.utils.find(
                    lambda m: lower_arg in m.name.lower() or lower_arg in m.display_name.lower(),
                    ctx.guild.members
                )
                if matched:
                    target = matched
                else:
                    embed = discord.Embed(
                        description=f"🔴 No user found matching `{target_arg}`.",
                        color=discord.Color.red()
                    )
                    return await ctx.send(embed=embed)

    balance = get_balance(target.id)
    desc = (
        f"Your current balance is **${balance}**"
        if target == ctx.author
        else f"**{getattr(target, 'display_name', target.name)}**'s current balance is **${balance}**"
    )

    embed = discord.Embed(
        description=desc,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(aliases=["rl"])
async def roulette(ctx, bet: int):
    user_id = ctx.author.id
    if bet < MIN_BET:
        embed = discord.Embed(
            description=f"🔴 Your bet must be at least **${MIN_BET}**",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if get_balance(user_id) < bet:
        embed = discord.Embed(
            description="🔴 You don’t have enough money",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Zufallszahl + Farbe
    number = random.randint(0, 36)
    if number == 0:
        color = "Green 🟢"
    elif number % 2 == 0:
        color = "Black ⚫️"
    else:
        color = "Red 🔴"

    # Gewinnchance berechnen mit Luck
    luck = get_luck_bonus(user_id)
    win_chance = 50 + luck
    roll = random.uniform(0, 100)
    win = roll <= win_chance

    if win:
        update_balance(user_id, bet)
        embed = discord.Embed(
            description=(
                 f"The number was **{number}({color})**\n\n"
                f"**Results**\n"
                f"You won **${bet * 2}**\n\n"
                f"💡Quick Tip\n"
                f"Get more luck using - **beach pray**"
            ),
            color=discord.Color.green()
        )
    else:
        update_balance(user_id, -bet)
        embed = discord.Embed(
            description=(
                 f"The number was **{number}({color})**\n\n"
                f"**Results**\n"
                f"You lost **${bet}**\n\n"
                f"💡Quick Tip\n"
                f"Get more luck using - **beach pray**"
            ),
            color=discord.Color.red()
        )

    # Kleines GIF oben rechts
    gif_url = "https://images-ext-1.discordapp.net/external/ch1XvTY8DwtClC4i-Z_pRYZ-j1GmtPgepO9A98CetgY/https/media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWM3Z2N3ZHN4OHJtZ3F3MHIzY3lkZmdrdXN3Z3dpM2pqeWJnZXJkYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/26uflBhaGt5lQsaCA/giphy.gif?width=338&height=238"
    embed.set_thumbnail(url=gif_url)

    await ctx.send(embed=embed)

@bot.command(aliases=["lb"])
async def leaderboard(ctx):
    user_id = ctx.author.id
    sorted_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(
        title="🏆 Leaderboard",
        color=discord.Color.gold()
    )

    # Top 10 anzeigen
    for idx, (uid, bal) in enumerate(sorted_users[:10], start=1):
        user = await bot.fetch_user(uid)
        embed.add_field(
            name=f"[ {idx} ] {user.name}",
            value=f"**${bal:,}**",
            inline=False
        )

    # Eigene Platzierung suchen
    user_rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), None)
    current_date = datetime.now().strftime("%-m/%-d/%y")  # z. B. 7/27/25

    embed.set_footer(text=f"Your global rank : #{user_rank} | {current_date}")
    await ctx.send(embed=embed)
    
@bot.command()
async def pray(ctx):
    user_id = ctx.author.id
    now = time.time()
    cooldown = 1800  # 30 Minuten

    # Cooldown prüfen
    if user_id in last_pray_time:
        elapsed = now - last_pray_time[user_id]
        if elapsed < cooldown:
            remaining = int(cooldown - elapsed)
            minutes = remaining // 60
            seconds = remaining % 60
            return await ctx.send(
                embed=discord.Embed(
                    description=f"🕒 You must wait **{minutes}m {seconds}s** before praying again.",
                    color=discord.Color.red()
                )
            )

    # Weighted Luck-Verteilung
    weighted_ranges = [
        (range(0, 11), 30),       # 0–10 → 30%
        (range(11, 31), 25),      # 11–30 → 25%
        (range(31, 51), 20),      # 31–50 → 20%
        (range(51, 76), 15),      # 51–75 → 15%
        (range(76, 101), 10)      # 76–100 → 10%
    ]
    ranges, weights = zip(*weighted_ranges)
    selected_range = random.choices(ranges, weights=weights, k=1)[0]
    luck = random.choice(selected_range)

    # Luck speichern & Zeit aktualisieren
    user_luck[user_id] = luck
    last_pray_time[user_id] = now

    # Embed senden
    embed = discord.Embed(
        title="🙏 You prayed . . .",
        description=f"You got **{luck}** points",
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@tasks.loop(hours=1)
async def decay_pet_stats():
    data = load_data()
    for user_id, user_data in data.get("users", {}).items():
        pet = user_data.get("pet")
        if not pet:
            continue

        pet["hunger"] = max(pet["hunger"] - random.randint(1, 3), 0)
        pet["happiness"] = max(pet["happiness"] - random.randint(1, 2), 0)
        pet["clean"] = max(pet["clean"] - random.randint(1, 3), 0)

        if pet["hunger"] == 0:
            try:
                user = await bot.fetch_user(int(user_id))
                embed = discord.Embed(
                    description="🔴 Your pet died because you didn’t feed him",
                    color=discord.Color.red()
                )
                await user.send(embed=embed)
            except:
                pass

            user_data.pop("pet", None)

    save_data(data)

@reset_econemy.error
@set_start_money.error
@clear_cooldowns.error
async def admin_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            embed=discord.Embed(
                description="🔴 You need admin permissions to use this command.",
                color=discord.Color.red()
            ),
            ephemeral=False
        )
bot.run.
