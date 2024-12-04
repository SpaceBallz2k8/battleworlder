# Battleworlder

A basic discord bot used to auto assign alliance members to spec ops missions

# Requirements

python 3.12+
discord.py
pandas
sqlite3

# Setup

YOU NEED TO CREATE YOUR OWN BOT AND OBTAIN A TOKEN ON THE DISCORD DEVELOPERS PANEL BEFORE USING THIS !!!

1. Clone the repository
2. run initialsetup.py - This will create your database and add the name aliases and the requirements for battleworld. You can edit these files as new characters and different requirements become available.
3. edit the main.py and add your discord token and your role name (allows the bot to operate with certain users)
4. Start the bot and wait for it to come online.
5. Run the !upload_data command. The bot will ask for the csv. Send your roster.csv to the channel your bot is in. If your role matches the bot will insert the roster data into the database.
6. Enjoy

# Usage

The bot has only a few commands. there are a few options in the search system.
The bot looks at requirements like r/y/g (red star, yellow star, gear) then the level required.
eg. r7 = red star 7 or greater (diamonds are classed as r8,r9,r10)
g16 = Gear 16 or greater
y6 = 6 Yellow Star or greater

!get_data spiderman r6 - searches for Spiderman 6 red star or greater in your roster. Sorts them by power (descending)

!req (x) where x is 1-5 (shows a list of requirements for that day)

!alias thanos (shows the aliases for names used in the roster file. Uses a wildcard search and shows all containing)

!upload_data - prompts the bot to ask for a replacement csv - use this when your roster changes

!assign (x) where x is 1-5 - Assign members to spec ops characters and display the results

The bot follows this pattern

Loads the requirements for the day

Loads the roster data

Searches for every character required for that day (48)

Stores the results in a dictionary for each member, along with assignment counts, dupe checks etc.

Sorts the found results into power order in the dictionary

Counts the results in each "search"

Starts assigning members to characters with the rarest first. Then if more are available it looks at power and tries to assign the lowest.


This might need tweaking, i have tried adding some balancing but if you have members with much higher powered rosters than others you will find they have less to assign. Essentially leaving the highest tcp to attack with.
