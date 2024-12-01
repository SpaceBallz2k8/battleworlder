# battleworlder
Discord bot for battleworld assignments

basic discord bot to be used for battleworld assignments (Marvel Strike Force)

!upload_data - triggers the bot to ask for a roster csv file
!restore_data - restore data from backup
!alias searchstring - shows clean names and names used in the roster csv
!assign day_number mission_number - eg !assign 1 1 will try to assign members to spec ops 1 in on day 1
!get_data toon r/g/y x - Find alliance members with searched item eg !get_data spiderman r7 will look for all spiderman's in your alliance with 7 red stars or greater

This is in a very early beta stage

I am trying to make the bot adhere to these rules

Only assign a max of 2 toons per alliance member in a single spec ops mission
Each member can only have 12 assignments total for a day
Every member found with the required toon is found then they are sorted by power and the lowest 5 are selected.
