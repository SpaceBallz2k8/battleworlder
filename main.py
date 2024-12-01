import discord
import shutil
import sqlite3
from discord.ext import commands
import os
import pandas as pd

# Bot Configuration
TOKEN = "your discord key here"  # Replace with your bot's token
ALLOWED_ROLE = "The Chosen Ones"  # Role allowed to upload CSV files - Create a discord role on your server and give it to the users you want to allow bot usage
db_path = "roster.db"  # You need to create this to start with
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
    character_name = " ".join(args[:-1])  # Combine everything before the criteria into the character name

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
            results += f"**{row['name']}** | Power: {row['power']} | Stars: {row['stars']} | Gear: {row['gear_tier']}\n"

        embed.add_field(name="Results", value=results[:1024], inline=False)
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
async def assign(ctx, day: int, mission: int):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Step 1: Fetch requirements for the specified day and mission
    query = """
        SELECT character_name, mission, type, level 
        FROM requirements 
        WHERE day = ? AND mission = ?
    """
    cursor.execute(query, (day, mission))
    requirements = cursor.fetchall()

    if not requirements:
        await ctx.send(f"No requirements found for Day {day}, Mission {mission}.")
        return

    # Step 2: Fetch the roster of alliance members
    query = """
        SELECT name, character_id, power, stars, level, guild_id 
        FROM roster
    """
    cursor.execute(query)
    roster = cursor.fetchall()

    # Prepare to track assignments
    assignments = {
        name: {
            "assignments": [],
            "total": 0,
            "missions": {m: 0 for m in range(1, 9)},
            "assigned_characters": set()  # To track assigned characters for each mission
        }
        for name, *_ in roster
    }

    # Step 3: Process each requirement for the day and mission
    failed_mission = False  # Track if the mission fails due to any character being unassigned

    for character_name, req_mission, char_type, required_level in requirements:
        # Filter eligible members who meet the requirements
        eligible_members = [
            member for member in roster
            if (
                member[4] >= required_level and  # member's level must meet or exceed the requirement
                assignments[member[0]]["total"] < 12 and  # Total assignments must be less than 12
                assignments[member[0]]["missions"][req_mission] < 2  # Max 2 assignments per mission
            )
        ]

        # Sort eligible members by power (ascending)
        eligible_members.sort(key=lambda x: x[2])  # x[2] is the Power

        assigned_count = 0

        # Assign members to the character for the mission
        for member in eligible_members:
            if assigned_count >= 5:  # Only assign up to 5 members per character
                break

            member_name = member[0]

            # Check if this character for the mission has already been assigned to this member
            if (character_name, req_mission) not in assignments[member_name]["assigned_characters"]:
                assignments[member_name]["assignments"].append((character_name, req_mission))
                assignments[member_name]["total"] += 1
                assignments[member_name]["missions"][req_mission] += 1
                assignments[member_name]["assigned_characters"].add((character_name, req_mission))  # Track assignment
                assigned_count += 1

        # If unable to fill all 5 slots for this character, mark the mission as failed
        if assigned_count < 5:
            failed_mission = True  # Mission fails if any character isn't fully assigned
            break  # No need to continue checking other characters

    # Step 4: Handle output based on whether the mission was successful or failed
    if failed_mission:
        await ctx.send(f"Mission {mission} for Day {day} cannot be completed due to unfilled character slots.")
    else:
        # Prepare embeds for each member with assignments for the specified day and mission
        output_lines = []
        for member_name, data in assignments.items():
            if data["assignments"]:
                # Filter for assignments that match the requested mission
                filtered_assignments = [
                    (char_name, mission) for char_name, mission in data["assignments"] if mission == mission
                ]

                if filtered_assignments:  # Only add if there are assignments for the requested mission
                    # Prepare the output line
                    output_line = f"{member_name} - Day {day} - " + " - ".join(
                        f"{char_name} (Mission: {mission})" for char_name, mission in filtered_assignments
                    )
                    output_lines.append(output_line)

        # Create a single embed for all relevant assignments
        embed = discord.Embed(
            title=f"Assignments for Day {day}, Mission {mission}",
            description="\n".join(output_lines),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

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
