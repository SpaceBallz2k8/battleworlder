import discord
import shutil
import sqlite3
from discord.ext import commands
from collections import defaultdict
import os
import pandas as pd

# Bot Configuration
TOKEN = "Token Here"  # Replace with your bot's token
ALLOWED_ROLE = "Your Role Here"  # Role allowed to upload CSV files
db_path = "roster.db"
data = None

# Define bot intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load data from the database for a specific guild
def load_data(guild_id):
    global data
    conn = sqlite3.connect(db_path)
    query = """
        SELECT roster.*, aliases.clean_name
        FROM roster
        LEFT JOIN aliases ON roster.character_id = aliases.character_id
        WHERE roster.guild_id = ?
    """
    data = pd.read_sql_query(query, conn, params=(guild_id,))
    conn.close()


# Load aliases into a dictionary for faster lookups
def load_aliases():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT character_id, clean_name FROM aliases")
    aliases = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return aliases


# Event to notify when the bot is ready
@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")


# Command to upload a new CSV file and update the database
@bot.command()
@commands.has_role(ALLOWED_ROLE)
async def upload_data(ctx):
    await ctx.send("Please upload the CSV file.")


@upload_data.error
async def upload_data_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You do not have permission to upload data.")


# Event to handle file uploads
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.attachments:
        if any(role.name == ALLOWED_ROLE for role in message.author.roles):
            for attachment in message.attachments:
                if attachment.filename.endswith('.csv'):
                    guild_id = message.guild.id
                    # Create a backup before replacing the current data
                    if os.path.exists(db_path):
                        shutil.copyfile(db_path, "backup_roster.db")
                    await attachment.save(attachment.filename)
                    update_database(attachment.filename, guild_id)
                    await message.channel.send("Data uploaded successfully! Backup created.")
                    return
    await bot.process_commands(message)


def update_database(csv_file, guild_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete old data for this guild
    cursor.execute("DELETE FROM roster WHERE guild_id = ?", (guild_id,))

    # Read the CSV file, use only the required columns
    df = pd.read_csv(csv_file)
    required_columns = ['Name', 'Character Id', 'Level', 'Power', 'Stars', 'Red Stars', 'Gear Tier', 'Basic', 'Special',
                        'Ultimate', 'Passive', 'ISO Class']

    # Ensure only required columns are kept
    try:
        df = df[required_columns]
    except KeyError as e:
        print(f"Missing required columns in CSV: {e}")
        return

    # Handle missing values by replacing with default values
    df = df.fillna({
        'Name': '',
        'Character Id': '',
        'Level': 0,
        'Power': 0,
        'Stars': 0,
        'Red Stars': 0,
        'Gear Tier': 0,
        'Basic': 0,
        'Special': 0,
        'Ultimate': 0,
        'Passive': 0,
        'ISO Class': ''
    })

    # Insert new data
    for _, row in df.iterrows():
        cursor.execute('''
            INSERT INTO roster (name, character_id, level, power, stars, red_stars, gear_tier, basic, special, ultimate, passive, iso_class, guild_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['Name'], row['Character Id'], row['Level'], row['Power'], row['Stars'], row['Red Stars'],
            row['Gear Tier'],
            row['Basic'], row['Special'], row['Ultimate'], row['Passive'], row['ISO Class'], guild_id
        ))

    conn.commit()
    conn.close()


# Command to search for a character with specified criteria
@bot.command()
async def get_data(ctx, *args):
    guild_id = ctx.guild.id
    load_data(guild_id)

    if data is None or data.empty:
        await ctx.send("No data has been uploaded yet.")
        return

    # Extract the criteria (e.g., r7, y5, g16) from the end of the command
    if not args or len(args) < 2:
        await ctx.send("Please provide a character name and a search criteria (e.g., !get_data Black Bolt r7).")
        return

    criteria = args[-1].lower()
    character_name = " ".join(args[:-1]).strip()  # Combine everything before the criteria into the character name

    # Determine the search criteria
    search_col = None
    criteria_value = None

    if criteria.startswith("y"):  # Yellow stars
        search_col = 'stars'
        criteria_value = int(criteria[1:])
    elif criteria.startswith("r"):  # Red stars
        search_col = 'red_stars'
        criteria_value = int(criteria[1:])
    elif criteria.startswith("g"):  # Gear tier
        search_col = 'gear_tier'
        criteria_value = int(criteria[1:])
    else:
        await ctx.send("Invalid criteria. Use yX for yellow stars, rX for red stars, or gX for gear tier.")
        return

    # Filter the data based on character name or ID
    filtered_data = data[
        (data['character_id'].str.lower() == character_name.lower()) |
        (data['clean_name'].str.lower() == character_name.lower())
        ]

    if search_col:
        filtered_data = filtered_data[filtered_data[search_col] >= criteria_value]

    # Sort the results by power in descending order
    filtered_data = filtered_data.sort_values(by='power', ascending=False)

    # Prepare the output message
    if filtered_data.empty:
        await ctx.send(f"No members found with {character_name} meeting {criteria}.")
    else:
        embed = discord.Embed(title=f"Results for {character_name} ({criteria})", color=discord.Color.blue())
        results = ""

        for index, row in filtered_data.iterrows():
            # Format the stars and red stars with icons
            yellow_stars = f"⭐ {row['stars']} " if row['stars'] > 0 else ""
            red_stars = f"🌟 {row['red_stars']} " if row['red_stars'] > 0 else ""
            result_line = f"**{row['name']}** | Power: {row['power']} | {yellow_stars}{red_stars}| Gear: {row['gear_tier']}\n"
            results += result_line

        # Split results into chunks without breaking lines
        max_field_length = 1024  # Discord field character limit
        results_fields = []
        while len(results) > max_field_length:
            # Find the last newline within the limit
            split_index = results.rfind('\n', 0, max_field_length)
            if split_index == -1:  # No newline found; break at max limit
                split_index = max_field_length

            results_fields.append(results[:split_index].strip())
            results = results[split_index:].lstrip()  # Remove leading whitespace for the next chunk

        # Add the remaining results if any
        if results:
            results_fields.append(results.strip())

        # Add each chunk as a new field in the embed without "Results Part" text
        for field in results_fields:
            embed.add_field(name="\u200b", value=field,
                            inline=False)  # Use an empty string for the name to avoid titles

        await ctx.send(embed=embed)


@bot.command()
async def alias(ctx, *search_terms):
    if not search_terms:
        await ctx.send("Please provide a search string. Example: !alias Thanos")
        return

    search_string = " ".join(search_terms).lower()

    # Connect to the database and fetch alias data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query for matches in the `aliases` table
    query = """
        SELECT DISTINCT clean_name, character_id 
        FROM aliases 
        WHERE LOWER(clean_name) LIKE ? OR LOWER(character_id) LIKE ?
    """
    cursor.execute(query, (f"%{search_string}%", f"%{search_string}%"))
    results = cursor.fetchall()
    conn.close()

    # Prepare the output
    if not results:
        await ctx.send(f"No aliases found for '{search_string}'.")
    else:
        embed = discord.Embed(
            title=f"Aliases for '{search_string}'",
            description="Results matching your search:",
            color=discord.Color.green()
        )

        for clean_name, character_id in results:
            embed.add_field(name=clean_name, value=f"Alias: {character_id}", inline=False)

        await ctx.send(embed=embed)


@bot.command()
async def req(ctx, day: int):
    # Connect to the database and fetch requirements data for the specified day
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to get all requirements for the specified day
    query = """
        SELECT character_name, mission, type, level 
        FROM requirements 
        WHERE day = ?
    """
    cursor.execute(query, (day,))
    results = cursor.fetchall()
    conn.close()

    # Prepare the output
    if not results:
        await ctx.send(f"No requirements found for day {day}.")
        return

    # Define the maximum number of fields per embed
    max_fields_per_embed = 25
    total_results = len(results)
    total_embeds = (total_results + max_fields_per_embed - 1) // max_fields_per_embed  # Calculate the number of embeds

    for i in range(total_embeds):
        # Create a new embed for each part
        embed = discord.Embed(
            title=f"Requirements for Day {day} (Part {i + 1}/{total_embeds})",
            description="Here are the requirements:",
            color=discord.Color.orange()
        )

        # Add fields to the embed
        for j in range(max_fields_per_embed):
            index = i * max_fields_per_embed + j
            if index >= total_results:
                break  # Stop if we've added all results

            character_name, mission, req_type, level = results[index]
            embed.add_field(name=character_name, value=f"Mission: {mission} | Type: {req_type} | Level: {level}", inline=False)

        await ctx.send(embed=embed)


@bot.command()
async def assign(ctx, day: int):
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Fetch the day's requirements
        cursor.execute("SELECT character_name, mission, type, level FROM requirements WHERE day = ?", (day,))
        requirements = sorted(cursor.fetchall(), key=lambda x: int(x[1]))  # Ensure missions are sorted numerically
        if not requirements:
            await ctx.send(f"No requirements found for day {day}.")
            return

        # Convert character names to IDs using the alias table
        alias_map = {}
        cursor.execute("SELECT clean_name, character_id FROM aliases")
        for clean_name, character_id in cursor.fetchall():
            alias_map[clean_name] = character_id

        # Fetch unique member names
        cursor.execute("SELECT DISTINCT name FROM roster")
        unique_members = [row[0] for row in cursor.fetchall()]

        # Fetch full roster data
        cursor.execute("SELECT name, character_id, power, level, stars, red_stars FROM roster")
        roster = cursor.fetchall()

        # Prepare a dictionary to store potential matches for each character requirement
        character_matches = defaultdict(list)
        for character_name, mission, req_type, req_level in requirements:
            character_id = alias_map.get(character_name)
            if not character_id:
                await ctx.send(f"Warning: Character '{character_name}' not found in alias table.")
                continue

            if req_type == 'G':  # Gear (level)
                matches = [row for row in roster if row[1] == character_id and row[3] >= req_level]
            elif req_type == 'Y':  # Yellow stars
                matches = [row for row in roster if row[1] == character_id and row[4] >= req_level]
            elif req_type == 'R':  # Red stars
                matches = [row for row in roster if row[1] == character_id and row[5] >= req_level]
            else:
                await ctx.send(f"Unknown requirement type: {req_type}")
                continue

            character_matches[(character_name, mission)] = matches

        # Process assignments with balancing logic
        mission_assignments = defaultdict(lambda: defaultdict(list))
        member_limits = {member: 12 for member in unique_members}
        member_assignments = {member: [] for member in unique_members}

        for (character_name, mission), matches in sorted(character_matches.items(), key=lambda x: len(x[1])):
            if len(matches) < 5:
                await ctx.send(f"Mission {mission} - {character_name}: Not enough members to fulfill requirement.")
                continue

            # Sort matches by power (ascending) and current assignment count (ascending)
            matches = sorted(
                matches,
                key=lambda x: (x[2], member_limits[x[0]])  # Sort by power first, then by remaining assignments
            )
            assigned = 0

            for match in matches:
                member_name = match[0]
                if assigned >= 5:
                    break
                if member_limits[member_name] > 0:
                    mission_assignments[mission][character_name].append(member_name)
                    member_assignments[member_name].append(f"{character_name}({mission})")
                    member_limits[member_name] -= 1
                    assigned += 1

        # Send mission assignments embeds in order
        for mission in sorted(mission_assignments.keys(), key=lambda x: int(x)):  # Ensure missions are sorted numerically
            mission_reqs = mission_assignments[mission]
            if mission_reqs:  # Only create embeds for missions with assignments
                mission_embed = discord.Embed(
                    title=f"Mission {mission} Assignments",
                    description=f"Assignments for Mission {mission}",
                    color=discord.Color.blue()
                )
                for character_name, assigned_members in mission_reqs.items():
                    mission_embed.add_field(
                        name=f"{character_name}",
                        value=", ".join(assigned_members),
                        inline=False
                    )
                await ctx.send(embed=mission_embed)

        # Create and send member summary embed
        summary_embed = discord.Embed(
            title="Member Assignment Summary",
            description="Total assignments per member",
            color=discord.Color.green()
        )

        for member, assignments in member_assignments.items():
            count = len(assignments)
            assignment_details = ", ".join(assignments) if assignments else "No assignments"
            summary_embed.add_field(
                name=f"{member} - Total Assignments: {count}",
                value=assignment_details,
                inline=False
            )

        await ctx.send(embed=summary_embed)

    finally:
        conn.close()




# Command to restore the previous backup
@bot.command()
@commands.has_role(ALLOWED_ROLE)
async def restore_data(ctx):
    if os.path.exists("backup_roster.db"):
        shutil.copyfile("backup_roster.db", db_path)  # Restore the backup
        load_data(ctx.guild.id)  # Reload the data after restore
        await ctx.send("Data has been restored from the backup.")
    else:
        await ctx.send("No backup data found.")


@restore_data.error
async def restore_data_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You do not have permission to restore data.")


# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)
