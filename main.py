import discord
from discord.ext import commands
from discord.ui import Button, View
import random
from discord import app_commands
import time
import asyncio
from datetime import datetime, timedelta
from discord.ext.commands import CheckFailure
import os
import json

intents = discord.Intents.default()
intents.message_content = True  # für Befehle wie beach cf 100
intents.guilds = True
intents.members = True

WHITELISTED_GUILDS = [
    1395416128599359489, 
    987654321098765432 
]

bot = commands.Bot(command_prefix='beach ', intents=intents)

# Guthaben & Luck
user_balances = {}
BASE_PATH = "data"
user_last_lottery = {}
lottery_data = {}
last_pray_time = {}
lottery_active = False
user_prison = {}
robbery_cooldowns = {}

user_luck = {}

START_BALANCE = 100000
MIN_BET = 5

@bot.check
async def globally_whitelist_guilds(ctx):
    if ctx.guild is None:
        return False  # Ignoriere DMs
    return ctx.guild.id in WHITELISTED_GUILDS

@bot.event
async def on_ready():
    try:
        await bot.add_cog(EconCommands(bot))  # COG laden!
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

def get_balance(user_id):
    return user_balances.get(user_id, START_BALANCE)


def update_balance(user_id, amount):
    user_balances[user_id] = get_balance(user_id) + amount


def get_luck_bonus(user_id):
    return user_luck.pop(user_id, 0)  # einmalig nutzbar

class EconCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reset-econemy", description="Reset all economy-related data")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_econemy(self, interaction: discord.Interaction):
        global user_balances, user_luck, last_pray_time, robbery_cooldowns, lottery_data, user_prison

        # Zurücksetzen der Daten
        user_balances.clear()
        user_luck.clear()
        last_pray_time.clear()
        robbery_cooldowns.clear()
        lottery_data.clear()
        user_prison.clear()

        embed = discord.Embed(
            description="🔴 Economy Reset Successful",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)  # Nur für Admin sichtbar

async def setup(bot):
    await bot.add_cog(EconCommands(bot))

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


@bot.command()
async def robbery(ctx):
    user_id = ctx.author.id
    now = time.time()

    # ⛓️ Im Gefängnis?
    if user_id in user_prison and now < user_prison[user_id]:
        remaining = int(user_prison[user_id] - now)
        minutes, seconds = divmod(remaining, 60)
        return await ctx.send(
            embed=discord.Embed(
                description=f"🕛 You are in jail. Wait **{minutes}m {seconds}s**.",
                color=discord.Color.red()
            )
        )

    # 🕒 Cooldown prüfen
    if user_id in robbery_cooldowns and now - robbery_cooldowns[user_id] < 1800:
        remaining = int(1800 - (now - robbery_cooldowns[user_id]))
        minutes, seconds = divmod(remaining, 60)
        return await ctx.send(
            embed=discord.Embed(
                description=f"🕒 You can rob again in **{minutes}m {seconds}s**.",
                color=discord.Color.orange()
            )
        )

    # 🎲 Erfolgschance mit Luck
    luck = user_luck.get(user_id, 0)
    base_chance = 0.4
    success_chance = min(base_chance + (luck / 250), 0.9)  # max 90% chance
    success = random.random() < success_chance

    robber = ctx.author.mention
    date = discord.utils.format_dt(discord.utils.utcnow(), style="F")

    if success:
        money = random.randint(1_000_000, 5_000_000)
        user_balances[user_id] = user_balances.get(user_id, 0) + money

        embed = discord.Embed(
            title="🚨 ROBBERY SUCCESS 🚨",
            description=f"You stole **${money:,}** from the bank\n\n"
                        f"> Date    : {date}\n"
                        f"> Robber  : {robber}\n\n"
                        f"💡 Quick Tip\nGet more luck using - **beach pray**",
            color=discord.Color.green()
        )
    else:
        loss = random.randint(5000, 10000)
        current_balance = user_balances.get(user_id, 0)
        lost = min(current_balance, loss)
        user_balances[user_id] = current_balance - lost
        prison_time = random.randint(240, 360)  # 4m bis 6m
        user_prison[user_id] = now + prison_time

        embed = discord.Embed(
            title="🚨 ROBBERY FAILED 🚨",
            description=f"You tried to steal **${random.randint(1_000_000, 5_000_000):,}** from the bank but failed\n\n"
                        f"> Date        : {date}\n"
                        f"> Robber      : {robber}\n"
                        f"> Prison Time : {int(prison_time // 60)}m\n"
                        f"> Lost Money  : ${lost:,}\n\n"
                        f"💡 Quick Tip\nGet more luck using - **beach pray**",
            color=discord.Color.red()
        )

    # 🕒 Cooldown setzen
    robbery_cooldowns[user_id] = now

    await ctx.send(embed=embed)

@bot.command()
async def balance(ctx):
    balance = get_balance(ctx.author.id)
    embed = discord.Embed(
        description=f"Your current balance is **${balance}**",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
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

@bot.command()
async def lottery(ctx):
    global lottery_active, lottery_data

    now = datetime.utcnow()
    user_id = ctx.author.id

    if user_id in user_last_lottery and now - user_last_lottery[user_id] < timedelta(days=1):
        return await ctx.send("🔴 You can only host one daily lottery per day.")

    if lottery_active:
        return await ctx.send("🔴 A daily lottery is already active. Please wait.")

    # Daten vorbereiten
    prize = random.randint(1_000_000, 5_000_000)
    tax = random.randint(5, 12)
    after_tax = prize - int(prize * tax / 100)
    ticket_price = int(prize * 0.4)

    lottery_data = {
        "host": user_id,
        "prize": prize,
        "tax": tax,
        "after_tax": after_tax,
        "ticket_price": ticket_price,
        "participants": {},
        "message": None
    }

    user_last_lottery[user_id] = now
    lottery_active = True

    embed = discord.Embed(
        title="🎰 LOTTERY 🎰",
        description=(
            "Lottery begins **Click the emoji below to participate**\n\n"
            f"**Prize Pool 💸**\n"
            f"> Total : **${prize}**\n"
            f"> Taxes : {tax}%\n"
            f"> After taxes : ${after_tax}\n\n"
            f"**Ticket info 🎟️**\n"
            f"> Price : ${ticket_price}\n"
            f"> Sold : 0\n"
            f"> Max per Player : 10\n\n"
            "💡Quick Tip\nluck points won’t affect your win chances"
        ),
        color=discord.Color.green()
    )

    class TicketMenu(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=f"{i} Ticket(s)", description=f"${i * ticket_price}", value=str(i))
                for i in range(1, 11)
            ]
            super().__init__(placeholder="Select number of tickets to buy", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            user = interaction.user
            amount = int(self.values[0])
            cost = amount * ticket_price

            user_balances.setdefault(user.id, 10_000_000)

            if user_balances[user.id] < cost:
                return await interaction.response.send_message("🔴 Not enough balance.", ephemeral=True)

            current = lottery_data["participants"].get(user.id, 0)
            if current + amount > 10:
                return await interaction.response.send_message("🔴 Max 10 tickets per player.", ephemeral=True)

            lottery_data["participants"][user.id] = current + amount
            user_balances[user.id] -= cost

            await interaction.response.send_message(f"✅ Bought {amount} ticket(s) for ${cost}.", ephemeral=True)
            await update_embed()

    class TicketView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(TicketMenu())

    view = TicketView()
    msg = await ctx.send(embed=embed, view=view)
    lottery_data["message"] = msg

    await asyncio.sleep(1200)  # 20 Minuten warten
    await draw_winner(ctx)


async def update_embed():
    msg = lottery_data["message"]
    embed = msg.embeds[0]
    total = sum(lottery_data["participants"].values())

    new_description = embed.description
    if "> Sold :" in new_description:
        new_description = '\n'.join([
            line if not line.startswith("> Sold :") else f"> Sold : {total}"
            for line in new_description.splitlines()
        ])

    embed.description = new_description
    await msg.edit(embed=embed)


async def draw_winner(ctx):
    global lottery_active

    all_entries = []
    for uid, count in lottery_data["participants"].items():
        all_entries.extend([uid] * count)

    if not all_entries:
        await ctx.send("🔴 No participants. Lottery cancelled.")
        lottery_active = False
        return

    winner_id = random.choice(all_entries)
    prize = lottery_data["after_tax"]
    tax = lottery_data["tax"]
    total_tickets = sum(lottery_data["participants"].values())
    winner = await ctx.guild.fetch_member(winner_id)

    user_balances[winner_id] += prize

    embed = discord.Embed(
        title="🎰 LOTTERY WINNERS 🎰",
        description=(
            f"Congratulations to our winner\n\n"
            f"> Winner : **{winner.display_name}**\n"
            f"> Price : ${prize}\n"
            f"> Taxes : {tax}%\n"
            f"> Date : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"> Tickets sold : {total_tickets}\n\n"
            "Luck points won’t affect your win chances"
        ),
        color=discord.Color.gold()
    )

    await ctx.send(embed=embed)
    lottery_active = False


bot.run("")
