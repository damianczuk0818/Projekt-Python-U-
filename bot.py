
import random
import asyncio
import disnake
from disnake.ext import commands
from disnake import Option

from disnake.utils import get

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True


bot = commands.Bot(command_prefix='!', intents=intents)

user_wins = {}
user_games = {}
parties = {}
queues = {}
user_parties = {}
current_queue = []
pending_invitations = {}
lobbies = {}
allowed_maps = ["Bind", "Haven", "Split", "Ascent", "Icebox", "Breeze", "Fracture", "Pearl", "Lotus", "Sunset", "Abyss"]
abort_requests = {}
party_join_times = {}

# Update these URLs with actual image URLs or placeholder URLs
map_images = {
    "Breeze": "https://static.wikia.nocookie.net/valorant/images/1/10/Loading_Screen_Breeze.png/revision/latest/scale-to-width-down/1000?cb=20210427160616",
    "Ascent": "https://static.wikia.nocookie.net/valorant/images/e/e7/Loading_Screen_Ascent.png/revision/latest/scale-to-width-down/1000?cb=20200607180020",
    "Bind": "https://static.wikia.nocookie.net/valorant/images/2/23/Loading_Screen_Bind.png/revision/latest/scale-to-width-down/1000?cb=20200620202316",
    "Fracture": "https://static.wikia.nocookie.net/valorant/images/f/fc/Loading_Screen_Fracture.png/revision/latest/scale-to-width-down/1000?cb=20210908143656",
    "Haven": "https://static.wikia.nocookie.net/valorant/images/7/70/Loading_Screen_Haven.png/revision/latest/scale-to-width-down/1000?cb=20200620202335",
    "Icebox": "https://static.wikia.nocookie.net/valorant/images/1/13/Loading_Screen_Icebox.png/revision/latest/scale-to-width-down/1000?cb=20201015084446",
    "Lotus": "https://static.wikia.nocookie.net/valorant/images/d/d0/Loading_Screen_Lotus.png/revision/latest/scale-to-width-down/1000?cb=20230106163526",
    "Pearl": "https://static.wikia.nocookie.net/valorant/images/a/af/Loading_Screen_Pearl.png/revision/latest?cb=20220622132842",
    "Split": "https://static.wikia.nocookie.net/valorant/images/d/d6/Loading_Screen_Split.png/revision/latest/scale-to-width-down/1000?cb=20230411161807",
    "Sunset": "https://static.wikia.nocookie.net/valorant/images/5/5c/Loading_Screen_Sunset.png/revision/latest?cb=20230829125442",
    "Abyss": "https://static.wikia.nocookie.net/valorant/images/6/61/Loading_Screen_Abyss.png/revision/latest/scale-to-width-down/1000?cb=20240612152007"
}


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    load_wins_from_file()
    load_games_from_file()


@bot.check
async def globally_check_channel(ctx):
    if ctx.channel.id not in ALLOWED_CHANNEL_ID:
        await ctx.send(f"This bot can only be used in <#1249849043614568509> channel.")
        return False
    return True


@bot.slash_command(name='force', description='Forcefully add a player to your party')
async def force(ctx, player_name: str):
    if ctx.author.id not in user_parties:
        await ctx.send("You must be part of a party to force add a player.")
        return

    party_name = user_parties[ctx.author.id]
    party = parties.get(party_name)

    if not party:
        await ctx.send("You are not currently in a party.")
        return

    leader = party['leader']

    if ctx.author != leader:
        await ctx.send("Only the party leader can force add a player.")
        return

    if len(party['members']) >= 10:
        await ctx.send("The party is already full and cannot accept more members.")
        return

    # Check if the player is already in a party
    if any(player_name.lower() in name.lower() for name in user_parties.values()):
        await ctx.send(f"The player '{player_name}' is already in a party.")
        return

    # Try to find the player in the guild
    player = ctx.guild.get_member_named(player_name)
    if not player:
        await ctx.send(f"Player '{player_name}' not found in the server.")
        return

    # Add the player to the party
    party['members'].append(player)
    user_parties[player.id] = party_name

    await ctx.send(f"Player has been forcefully added to the party '{party_name}'.")


@bot.slash_command(name='create_party', description='Create a new party')
async def create_party(ctx, name: str):
    if ctx.author.id in user_parties:
        # Check if the user is already associated with a party
        if user_parties[ctx.author.id] in parties:
            await ctx.send("You've already created a party. Disband your current party to create a new one.")
            return
        else:
            # Remove the user from user_parties if they are associated with a party that no longer exists
            del user_parties[ctx.author.id]

    if name in parties:
        await ctx.send(f"Party '{name}' already exists.")
    else:
        # Create the new party
        leader = ctx.author
        parties[name] = {'leader': leader, 'members': [leader]}
        user_parties[ctx.author.id] = name
        await ctx.send(f"Party '{name}' created by {leader.mention}.")


@bot.slash_command(name='invite_user', description='Invite user to your party')
async def invite_user(ctx, inviting_party_name: str, invited_user_name: str):
    if inviting_party_name not in parties:
        await ctx.send("The party you are trying to invite from does not exist.")
        return

    inviting_party = parties[inviting_party_name]
    leader = inviting_party['leader']

    if ctx.author != leader:
        await ctx.send("Only the party leader can invite another user.")
        return

    if len(inviting_party['members']) >= 10:
        await ctx.send("The party is full and cannot accept more members.")
        return

    invited_user = ctx.guild.get_member_named(invited_user_name)
    if invited_user:
        if invited_user in user_parties:
            await ctx.send(f"{invited_user.mention} is already in a party.")
            return

        pending_invitations[invited_user] = inviting_party_name
        await ctx.send(
            f"{invited_user.mention} has been invited to join the party '{inviting_party_name}'. To accept, use `/accept {inviting_party_name}`.")
    else:
        await ctx.send(f"User '{invited_user_name}' does not exist.")


@bot.slash_command(name='accept', description='accept an invitation')
async def accept(ctx, inviting_party_name: str):
    if inviting_party_name not in parties:
        await ctx.send(f"Party '{inviting_party_name}' does not exist.")
        return

    if ctx.author in user_parties and user_parties[ctx.author] in parties:
        # Check if the author is trying to accept an invitation from another party
        if inviting_party_name == user_parties[ctx.author]:
            await ctx.send("You cannot accept an invitation because you have already created your own party.")
            return

    if ctx.author not in user_parties and ctx.author not in pending_invitations:
        await ctx.send("You are not a member of any party.")
        return

    if ctx.author in pending_invitations and pending_invitations[ctx.author] == inviting_party_name:
        inviting_party = parties[inviting_party_name]
        accepting_party_name = user_parties.get(ctx.author)

        if accepting_party_name:
            accepting_party = parties[accepting_party_name]
            if len(inviting_party['members']) + len(accepting_party['members']) > 10:
                await ctx.send(f"Merging these parties would exceed the member limit of 10.")
                return

            inviting_party['members'].extend(accepting_party['members'])
            for member in accepting_party['members']:
                user_parties[member] = inviting_party_name

            del parties[accepting_party_name]
            del pending_invitations[ctx.author]  # Changed to ctx.author

            await ctx.send(
                f"{accepting_party_name} accepted the invitation from {inviting_party_name}. now use /join_queue start.")
        else:
            inviting_party['members'].append(ctx.author)
            user_parties[ctx.author] = inviting_party_name
            del pending_invitations[ctx.author]
            await ctx.send(f"{ctx.author.mention} accepted the invitation to join the party '{inviting_party_name}'.")
    else:
        await ctx.send(f"You or your party has not been invited by '{inviting_party_name}'.")


@bot.slash_command(name='merge_party', description='Merge two parties into one and join queue as 10 players')
async def merge_party(
    ctx: disnake.ApplicationCommandInteraction,
    invited_party_name: str = Option(
        name="invited_party_name",
        description="Name of the party to merge with",
        type=disnake.OptionType.string,
        required=True
    )
):
    if invited_party_name not in parties:
        await ctx.send(f"Party '{invited_party_name}' does not exist.")
        return

    if ctx.author.id not in user_parties:
        await ctx.send("You must be part of a party to merge with another party.",ephemeral=True)
        return

    current_party_name = user_parties[ctx.author.id]
    current_party = parties[current_party_name]
    leader = current_party['leader']

    if ctx.author != leader:
        await ctx.send("Only the party leader can merge with another party.")
        return

    if current_party_name == invited_party_name:
        await ctx.send("You cannot merge your party with itself.")
        return

    invited_party = parties[invited_party_name]
    invited_leader = invited_party['leader']

    if len(invited_party['members']) + len(current_party['members']) > 10:
        await ctx.send("Merging these parties would exceed the member limit of 10.")
        return

    if invited_party_name in pending_invitations:
        await ctx.send("A merge request has already been sent to this party.")
        return

    # Set up a merge request
    pending_invitations[invited_party_name] = current_party_name
    await ctx.send(f"A merge request has been sent to the leader of party '{invited_party_name}'. Use `/confirm_merge` to agree.")

@bot.slash_command(name='confirm_merge',description='Accept request about merging their party into yours')
async def confirm_merge(ctx: disnake.ApplicationCommandInteraction):
    if ctx.author.id not in user_parties:
        await ctx.send("You must be part of a party to confirm a merge.", ephemeral=True)
        return

    accepting_party_name = user_parties[ctx.author.id]
    accepting_party = parties[accepting_party_name]
    leader = accepting_party['leader']

    if ctx.author != leader:
        await ctx.send("Only the party leader can confirm a merge.", ephemeral=True)
        return

    if accepting_party_name not in pending_invitations:
        await ctx.send("There are no pending merge requests for your party.", ephemeral=True)
        return

    inviting_party_name = pending_invitations[accepting_party_name]

    if inviting_party_name not in parties:
        await ctx.send(f"The inviting party '{inviting_party_name}' no longer exists.", ephemeral=True)
        del pending_invitations[accepting_party_name]
        return

    inviting_party = parties[inviting_party_name]
    inviting_leader = inviting_party['leader']

    if len(accepting_party['members']) + len(inviting_party['members']) > 10:
        await ctx.send("Merging these parties would exceed the member limit of 10.", ephemeral=True)
        return

    # Merge the parties
    accepting_party['members'].extend(inviting_party['members'])

    # Update user_parties to reflect the new merged party
    for member in inviting_party['members']:
        user_parties[member.id] = accepting_party_name

    # Clean up
    del parties[inviting_party_name]
    del pending_invitations[accepting_party_name]

    await ctx.send(f"Merge succeed, players from '{inviting_party_name}' party has been transfered to '{accepting_party_name}'.")

@bot.slash_command(name='show_party', description='show party members')
async def show_party(ctx, name: str = None):
    if name is None:
        # If no name is provided, check the party of the player invoking the command
        player_id = ctx.author.id
        player_party = None

        for party_name, party_data in parties.items():
            if player_id in [member.id for member in party_data['members']]:
                player_party = party_name
                break

        if player_party is None:
            await ctx.send("You are not in any party.")
        else:
            members = ', '.join([member.mention for member in parties[player_party]['members']])
            await ctx.send(f"Your party '{player_party}' members: {members}")
        return

    if name not in parties:
        await ctx.send(f"Party '{name}' does not exist.")
        return

    party = parties[name]
    members = ', '.join([member.mention for member in party['members']])
    await ctx.send(f"Party '{name}' members: {members}")


@bot.slash_command(name='join_queue', description='Join the queue')
async def join_queue(ctx: disnake.ApplicationCommandInteraction):
    if ctx.author.id not in user_parties:
        await ctx.send(content="You must be part of a party to join the queue.", ephemeral=True)
        return

    party_name = user_parties[ctx.author.id]
    party = parties.get(party_name)

    if not party:
        await ctx.send(content="You are not currently in a party.", ephemeral=True)
        return

    if ctx.author != party['leader']:
        await ctx.send(content="Only the party leader can join the queue.", ephemeral=True)
        return

    if len(party['members']) not in [5, 10]:  # Updated to 5 or 10 members
        await ctx.send(content="Your party must have exactly 5 or 10 members to join the queue.", ephemeral=True)
        return

    if any(member in current_queue for member in party['members']):
        await ctx.send(content="One or more members of your party are already in the queue.", ephemeral=True)
        return

    if any(ctx.author in lobby['members'] for lobby in lobbies.values()):
        await ctx.send(content="Your party is currently in a lobby and must report the loss before joining the queue again.", ephemeral=True)
        return

    # Check if adding the new party members will exceed the queue limit
    if len(current_queue) + len(party['members']) > 10:
        # If adding the party exceeds the limit, create a new queue and add the party there
        global new_queue
        if 'new_queue' not in globals():
            new_queue = []

        new_queue.extend(party['members'])
        new_queue_length = len(new_queue)
        new_queue_members = ', '.join([member.mention for member in new_queue])
        await ctx.send(content=f"{party_name} joined the new queue. \n> 5v5 **[{new_queue_length}/10]** Players: {new_queue_members}")

        if new_queue_length == 10:
            await ctx.send(content="__New queue is full with 10 players__. Starting the **ban phase**.")
            await start_ban_phase(ctx, new_queue)
        else:
            # Start the timer to remove the party from the new queue after 20 minutes
            party_join_times[party_name] = asyncio.create_task(schedule_queue_removal(ctx, party_name, new_queue))

        return

    # Add the party to the current queue
    current_queue.extend(party['members'])
    queue_length = len(current_queue)
    queue_members = ', '.join([member.mention for member in current_queue])
    await ctx.send(content=f"{party_name} joined the queue. \n> 5v5 **[{queue_length}/10]** Players: {queue_members}")

    if queue_length == 10:
        await ctx.send(content="__Queue is full with 10 players__. Starting the **ban phase**.")
        await start_ban_phase(ctx, current_queue)
    else:
        # Start the timer to remove the party from the queue after 20 minutes
        party_join_times[party_name] = asyncio.create_task(schedule_queue_removal(ctx, party_name, current_queue))

async def schedule_queue_removal(ctx, party_name, queue):
    await asyncio.sleep(20 * 60)  # Wait for 20 minutes

    # Check if the party is still in the queue
    party = parties.get(party_name)

    if not party:
        await ctx.send(content=f"{party_name} is no longer in a valid state to be in the queue.", ephemeral=True)
        return

    if all(member in queue for member in party['members']):
        for member in party['members']:
            if member in queue:
                queue.remove(member)
        await ctx.send(content=f"{party_name} has been removed from the queue after 20 minutes due to anty afk system.", ephemeral=True)

@bot.slash_command(name='queue', description='inspect players in queue')
async def queue(ctx):
    queue_length = len(current_queue)
    queue_members = ', '.join([member.mention for member in current_queue])
    await ctx.send(f"> 5v5 **[{queue_length}/10]** Players: {queue_members}")


@bot.slash_command(name='leave_queue', description='leave queue with your party')
async def leave_queue(ctx: disnake.ApplicationCommandInteraction):
    if ctx.author.id not in user_parties:
        await ctx.send("You must be part of a party to leave the queue.",ephemeral=True)
        return

    party_name = user_parties[ctx.author.id]
    party = parties.get(party_name)

    if not party:
        await ctx.send("Your party does not exist or has been disbanded.")
        return

    if ctx.author != party['leader']:
        await ctx.send("Only the party leader can leave the queue.")
        return

    if not any(member in current_queue for member in party['members']):
        await ctx.send("Your party is not in the queue.")
        return

    # Remove party members from the queue
    for member in party['members']:
        if member in current_queue:
            current_queue.remove(member)

    queue_length = len(current_queue)
    queue_members = ', '.join([member.mention for member in current_queue])
    await ctx.send(f"{party_name} left the queue.\n> 5v5 **[{queue_length}/10]** Players: {queue_members}")


def save_wins_to_file(user_wins):
    with open('user_wins.txt', 'w') as file:
        for user, wins in user_wins.items():
            file.write(f"{user}:{wins}\n")


def load_wins_from_file():
    global user_wins
    try:
        with open('user_wins.txt', 'r') as file:
            user_wins_data = file.readlines()
        for line in user_wins_data:
            if line.strip():  # Ignore empty lines
                try:
                    user_id, wins = line.strip().split(':')
                    user_wins[int(user_id)] = int(wins)
                except ValueError:
                    print(f"Skipping line due to parsing error: {line.strip()}")
    except FileNotFoundError:
        print("No win data file found. Starting with an empty win count.")


def save_games_to_file(user_games):
    with open('user_games.txt', 'w') as file:
        for user, games in user_games.items():
            file.write(f"{user}:{games}\n")


def load_games_from_file():
    global user_games
    try:
        with open('user_games.txt', 'r') as file:
            user_games_data = file.readlines()
        for line in user_games_data:
            if line.strip():  # Ignore empty lines
                try:
                    user_id, games = line.strip().split(':')
                    user_games[int(user_id)] = int(games)
                except ValueError:
                    print(f"Skipping line due to parsing error: {line.strip()}")
    except FileNotFoundError:
        print("No games data file found. Starting with an empty games count.")


@bot.slash_command(name='report_loss', description='Report your team\'s loss')
async def report_loss(inter):
    print(f"User {inter.author.id} invoked /report_loss")

    if inter.author.id not in user_parties:
        await inter.send("You must be part of a party to report a loss.", ephemeral=True)
        return

    party_name = user_parties[inter.author.id]
    party = parties.get(party_name)

    print(f"Party found: {party_name}, {party}")

    if not party:
        await inter.send("You are not currently in a party.")
        return

    lobby_id = None
    for lid, lobby in lobbies.items():
        if any(member.id in [p.id for p in party['members']] for member in lobby['members']):
            lobby_id = lid
            break

    print(f"Lobby ID found: {lobby_id}")

    if lobby_id is None:
        await inter.send("Your party is not in a lobby.",ephemeral=True)
        return

    if lobbies[lobby_id]['ban_phase_active']:
        await inter.send("Cannot report loss during the ban phase.")
        return

    # Ensure the lobby has exactly 10 players
    if len(lobbies[lobby_id]['members']) != 10:
        await inter.send("A loss can only be reported if there are exactly 10 players in the lobby.")
        return

    try:
        # Determine the position of the reporting player in the lobby
        author_position = [member.id for member in lobbies[lobby_id]['members']].index(inter.author.id)
    except ValueError:
        await inter.send("You are not recognized as a member of this lobby.")
        print(
            f"User {inter.author.id} is not in the lobby members list: {[member.id for member in lobbies[lobby_id]['members']]}")
        return

    print(f"User position in the lobby: {author_position}")

    # Only allow 1st (0-indexed) and 6th (5-indexed) player to use report loss
    if author_position not in [0, 5]:
        await inter.send("Only leaders can report a loss.") #Only the 1st and 6th players can report a loss.
        return

    # Check if the 1st player is the party leader
    if author_position == 0 and inter.author.id != party['leader'].id:
        await inter.send("Only the party leader can report a loss.")
        return

    # Determine the winning team based on the reporting player
    team_a = lobbies[lobby_id]['members'][:5]
    team_b = lobbies[lobby_id]['members'][5:]

    if author_position == 0:  # 1st player (Team A)
        winning_team = team_b  # Team B wins
    elif author_position == 5:  # 6th player (Team B)
        winning_team = team_a  # Team A wins

    print(f"Winning team: {winning_team}")

    # Load current wins and games from files
    load_wins_from_file()
    load_games_from_file()

    # Increment win count for each member of the winning team
    for member in winning_team:
        user_wins[member.id] = user_wins.get(member.id, 0) + 1

    # Increment games played for each member in the lobby
    for member in lobbies[lobby_id]['members']:
        user_games[member.id] = user_games.get(member.id, 0) + 1

    # Save updated win counts and games played to text files
    save_wins_to_file(user_wins)
    save_games_to_file(user_games)

    # Remove all players from the lobby
    lobbies.pop(lobby_id)

    await inter.send(f"The loss has been reported. Players in the winning team have been awarded a win.")


@bot.slash_command(name='wins', description='Wins leaderboard')
async def wins(inter):
    user_wins = {}

    # Read user wins from the file
    try:
        with open('user_wins.txt', 'r') as file:
            user_wins_data = file.readlines()
    except FileNotFoundError:
        await inter.send("No win data found.")
        return

    # Parse the file and handle potential errors
    for line in user_wins_data:
        if line.strip():  # Ignore empty lines
            try:
                user_id, wins = line.strip().split(':')
                user_wins[int(user_id)] = int(wins)
            except ValueError:
                # Handle lines that cannot be parsed
                print(f"Skipping line due to parsing error: {line.strip()}")
                pass

    # Check if the invoking user has any wins
    if inter.author.id not in user_wins:
        await inter.send("You haven't won any games yet.")
        return

    user_wins_count = user_wins[inter.author.id]

    # Sort users by wins and get the top 10
    top_players = sorted(user_wins.items(), key=lambda item: item[1], reverse=True)[:10]

    # Prepare the leaderboard message
    leaderboard_message = ":trophy: **Wins Leaderboard:** :trophy:\n"
    position = 1
    for player_id, wins in top_players:
        try:
            member = await bot.fetch_user(player_id)
            leaderboard_message += f"> **{position}**. {member.name} : {wins} wins\n"
        except disnake.NotFound:
            # Handle the case where a user ID is not found
            leaderboard_message += f"{position}. Unknown User: {wins} wins\n"
        position += 1

    # Add the invoking user's score to the leaderboard message
    leaderboard_message += f"\n __*Your Wins:*__  {user_wins_count}"

    # Send the leaderboard message
    await inter.send(leaderboard_message)

@bot.slash_command(name='stats', description='Your game statistics')
async def stats(inter, nickname: str = None):
    load_wins_from_file()
    load_games_from_file()

    if nickname:
        user = get(inter.guild.members, name=nickname)
        if user is None:
            await inter.send(f"User with nickname '{nickname}' not found.")
            return
        user_id = user.id
    else:
        user_id = inter.author.id

    wins = user_wins.get(user_id, 0)
    games = user_games.get(user_id, 0)

    if games == 0:
        winrate = 0
    else:
        winrate = (wins / games) * 100

    stats_message = (
        f"**Stats for {user.name if nickname else 'You'}:**\n"
        f"> Games Played: {games}\n"
        f"> Games Won: {wins}\n"
        f"> Win Rate: {winrate:.2f}%"
    )

    await inter.send(stats_message)

@bot.slash_command(name='abort', description='Send request about match abort')
async def abort(ctx):
    if ctx.author.id not in user_parties:
        await ctx.send("You must be part of a party to initiate an abort request.", ephemeral=True)
        return

    party_name = user_parties[ctx.author.id]
    party = parties[party_name]

    lobby_id = None
    for lid, lobby in lobbies.items():
        if any(member.id == ctx.author.id for member in lobby['members']):
            lobby_id = lid
            break

    if lobby_id is None:
        await ctx.send("Your party is not in a lobby.", ephemeral=True)
        return

    lobby = lobbies[lobby_id]

    # Ensure there are exactly 10 players in the lobby
    if len(lobby['members']) != 10:
        await ctx.send("An abort request can only be initiated if there are exactly 10 players in the lobby.")
        return

    # Check if the author is the party leader or the sixth player
    if ctx.author == lobby['members'][0] or ctx.author == lobby['members'][5]:
        # Check if there's already an active abort request for the lobby
        if lobby_id in abort_requests:
            # Remove lobby and abort request
            del lobbies[lobby_id]
            del abort_requests[lobby_id]
            await ctx.send("The match has been aborted. Players have been removed from the lobby.")
            return

        # Set the flag for pending abort request
        abort_requests[lobby_id] = ctx.author

        # Find the other player who can initiate abort
        other_player = lobby['members'][5] if ctx.author == lobby['members'][0] else lobby['members'][0]

        await ctx.send(f"{other_player.mention}, {ctx.author.mention} has initiated an abort request. Use `/abort` to confirm.")

        # Check if both the first and sixth players have initiated the abort request
        if lobby['members'][0] in abort_requests.values() and lobby['members'][5] in abort_requests.values():
            # Remove lobby and abort request
            del lobbies[lobby_id]
            del abort_requests[lobby_id]
            await ctx.send("The match has been aborted. Players have been removed from the lobby.")
    else:
        await ctx.send("Only the party leaders can initiate an abort request.")
#Only the party leader (first player) or the sixth player can initiate an abort request.

@bot.slash_command(name='ban', description='Ban a map during ban phase')
async def ban(ctx, map_name: str):
    if ctx.author.id not in user_parties:
        await ctx.send("You must be in a party to ban a map.")
        return

    party_name = user_parties[ctx.author.id]
    party = parties.get(party_name)

    if not party or ctx.author not in party['members']:
        await ctx.send("You are not in an active lobby with a party.")
        return

    lobby_id = None
    for lid, lobby in lobbies.items():
        if any(member.id == ctx.author.id for member in lobby['members']):
            lobby_id = lid
            break

    if lobby_id is None or not lobbies[lobby_id]['ban_phase_active']:
        await ctx.send("There is no active ban phase in your lobby.")
        return

    ban_data = lobbies[lobby_id]

    # Ensure the sixth player is considered as a leader
    sixth_player = ban_data['members'][5]
    if sixth_player.id not in user_parties:
        user_parties[sixth_player.id] = f"party_{sixth_player.id}"
        parties[user_parties[sixth_player.id]] = {'leader': sixth_player, 'members': [sixth_player]}

    # Determine the current player's index in the party
    party_index = ban_data['members'].index(ctx.author)

    # Determine whose turn it is to ban
    current_turn = ban_data['ban_turn']
    if current_turn % 2 == 0:
        current_player = ban_data['members'][5]
    else:
        current_player = ban_data['members'][0]

    # Check if it's the current player's turn to ban
    if ctx.author != current_player:
        await ctx.send("It's not your turn to ban a map.")
        return

    # Check if the map name is valid
    if map_name not in allowed_maps:
        await ctx.send(f"{map_name} is not an allowed map to ban.\n /maps to check all available maps to ban.", ephemeral=True)
        return

    # Check if the map has already been banned
    if map_name in ban_data['bans']:
        await ctx.send("This map is already banned.")
        return

    # Ban the map
    ban_data['bans'].append(map_name)
    await ctx.send(f"{map_name} has been banned. :no_entry_sign:")

    # Check if all maps have been banned
    if len(ban_data['bans']) == 10:
        remaining_map = [map for map in allowed_maps if map not in ban_data['bans']][0]
        await ctx.send(f"All maps have been banned except {remaining_map}. **{remaining_map}** will be played.")
        ban_data['ban_phase_active'] = False
        await send_match_details(ctx, lobby_id, remaining_map)  # Call to send the match details
        return

    # List remaining maps to ban
    remaining_maps = [map for map in allowed_maps if map not in ban_data['bans']]
    await ctx.send(f"**Remaining maps to ban:** {', '.join(remaining_maps)}")

    # Handle special case for the last ban (turn 9), only the sixth player can ban
    if len(remaining_maps) == 1:
        await ctx.send(
            f"**Remaining map to ban:** {', '.join(remaining_maps)} \n {sixth_player.mention}, it's your turn to ban the last map. Use the command `/ban <map_name>` again.")
        return

    # Increment the ban turn for the next player
    ban_data['ban_turn'] += 1

    # Determine the next player to ban
    if ban_data['ban_turn'] == 10:
        next_player = current_player
    elif ban_data['ban_turn'] % 2 == 0:
        next_player = ban_data['members'][5]
    else:
        next_player = ban_data['members'][0]

    # Mention the next player
    await ctx.send(f"{next_player.mention}, it's your turn to ban a map. Use the command `/ban <map_name>`.")


@bot.slash_command(name='party_leave', description='leave your party')
async def party_leave(ctx):
    if ctx.author not in user_parties:
        await ctx.send("You can't leave try /party_remove .")
        return

    party_name = user_parties[ctx.author]
    party = parties[party_name]

    if ctx.author == party['leader']:
        await ctx.send("The party leader cannot leave the party. Use /party_remove to disband the party.")
        return

    if any(ctx.author in lobby['members'] for lobby in lobbies.values()):
        await ctx.send("You cannot leave the party during the ban phase.")
        return

    party['members'].remove(ctx.author)
    del user_parties[ctx.author]
    await ctx.send(f"{ctx.author.mention} has left the party '{party_name}'.")

    if len(party['members']) == 0:
        del parties[party_name]


@bot.slash_command(name='party_remove', description='Disband your whole party')
async def party_remove(ctx):
    if ctx.author.id not in user_parties:
        await ctx.send("You are not in a party.")
        return

    party_name = user_parties[ctx.author.id]
    party = parties.get(party_name)

    if not party:
        await ctx.send("You are not currently in a party.")
        return

    if ctx.author != party['leader']:
        await ctx.send("Only the party leader can disband the party.")
        return

    if any(ctx.author in lobby['members'] for lobby in lobbies.values()):
        await ctx.send("You cannot disband the party during the ban phase.")
        return

    # Remove each member from user_parties
    for member_id in party['members']:
        if member_id in user_parties:
            del user_parties[member_id]

    # Remove party from parties
    if party_name in parties:
        del parties[party_name]

    await ctx.send(f"Party '{party_name}' has been disbanded by {ctx.author.mention}.")


@bot.slash_command(name='lobby', description='display players that are already in match lobby')
async def lobby(ctx):
    if not lobbies:
        await ctx.send("There are currently no active lobbies.")
        return

    for lobby_id, lobby_data in lobbies.items():
        members = ', '.join([member.mention for member in lobby_data['members']])
        await ctx.send(f"Lobby nr.{lobby_id} members: {members}")


async def start_ban_phase(ctx, queue):
    global current_queue, new_queue

    lobby_id = len(lobbies) + 1
    lobbies[lobby_id] = {
        'members': queue.copy(),
        'bans': [],
        'ban_turn': 0,
        'ban_phase_active': True
    }

    # Clear the appropriate queue
    if queue == current_queue:
        current_queue.clear()
    else:
        new_queue.clear()

    lobby = lobbies[lobby_id]
    first_member = lobby['members'][0]
    sixth_player = lobby['members'][5]
    await ctx.send(f"{sixth_player.mention}, 1st ban is yours. Use `/ban Mapname` to ban a map.\n /maps to check all available maps")
async def send_match_details(ctx, lobby_id, map_name):
    lobby = lobbies[lobby_id]
    team_a = lobby['members'][:5]
    team_b = lobby['members'][5:]
    team_a_mentions = '\n'.join([member.mention for member in team_a])
    team_b_mentions = '\n'.join([member.mention for member in team_b])
    map_image_url = map_images.get(map_name, "")
    starting_team = random.choice(["Team A", "Team B"])

    embed = disnake.Embed(
        title=f"Match Details for Lobby {lobby_id}",
        color=disnake.Color.blue()
    )
    embed.add_field(name="Team A", value=team_a_mentions, inline=True)
    embed.add_field(name="\u200B", value=f"**Map:** {map_name}\n{starting_team} starts as defenders", inline=True)
    embed.add_field(name="Team B", value=team_b_mentions, inline=True)

    if map_image_url:
        embed.set_image(url=map_image_url)

    await ctx.send(embed=embed)

@bot.slash_command(name='maps', description='show all maps')
async def maps(ctx):
    map_list = "\n".join([f"- {map_name}" for map_name in allowed_maps])
    await ctx.send(f"Available maps:\n{map_list}",ephemeral=True)

@bot.slash_command(name='commands', description='display more info about commands')
async def commands(ctx, command=None):

    if command is None:
        help_message = """```fix\nAvailable commands:\n
/create_party (PartyName) - Create a new party.
/merge_party (TheirPartyName)- ask another leader to join his party and queue as 10 if current queue is 5/10 (party that will sent request will lost leader previllages after acceptation)
/invite_user - Invite a user to join your party.\n(it must be exact discord account username/be aware of upper/lowercases)\nExample: /invite_user YourPartyName _name123-__-(ping wont work)

/show_party (PartyName) - Show the members of a party.
/party_leave - Leave your current party.
/party_remove - Disband your whole current party.

/queue - Display active queues and their members.
/lobby - Display active lobbies and their members.
/join_queue - Join the queue with your party.
/leave_queue - Leave the queue with your party.

/report_loss - Report a loss for your party.(works only if ban phase ends)
/abort - Abort the current lobby if all party leaders agree.(works during ban phase and after)

/ban (Map) - command to ban maps in the match lobby.
/maps - List all available maps.
/wins - check leaderboard of total wins
/stats - check your/someone stats (it must be exact discord account username)
```"""
        await ctx.send(help_message,ephemeral=True)
    else:
        # Add custom help messages for specific commands if needed
        pass

@bot.command()
async def msg1(ctx, command=None):

    if command is None:
        help_message = """
Welcome to **CX Valorant Bot** - Your 5v5 Scrim Organizer! 🎮

Hello, Agents! I'm Valorant Bot, your go-to assistant for organizing and coordinating 5v5 scrim matches right here on Discord.

I'm here to make your scrim experience seamless and enjoyable. From setting up teams and managing match logistics to ensuring fair play and resolving disputes, I've got you covered.

Let's dive into the action and perfect those strategies together! See you in the game, Agents!

```fix
     COMMAND  ;  PARAMETERS
/create_party   name
/merge_party    AnotherPartyName
/confirm_merge
/invite_user    YourPartyName Username
/accept         NameOfPartyThatInvitedYou
/show_party     NameOfParty
/join_queue
/queue
/leave_queue
/party_leave
/party_remove
/lobby
/report_loss
/abort
/maps
/stats          DiscordName
/wins

for more info use /commands
```"""
        await ctx.send(help_message)
    else:
        # Add custom help messages for specific commands if needed
        pass
@bot.command()
async def msg2(ctx, command=None):

    if command is None:
        help_message = """# __STANDARD POST:__\n\n
        
**Hello, I am CX Valorant Bot.**
Last season, I was Platinum 2, but I am currently Gold 3. I have aspirations to reach higher ranks with my new premade team.
my mains are Sova and Skye so im initiator 
Please feel free to direct message me.\n
_[Optional screenshot of profile/tracker/achievements/etc]_
        
        """

        await ctx.send(help_message)
    else:
        # Add custom help messages for specific commands if needed
        pass


@bot.command()
async def msg3(ctx, command=None):
    if command is None:
        help_message = """# __STANDARD POST:__\n\n

**Hello, My team is called CX Valorant Bot Team.**
Last season, our 5-stack reached high Immortal, but one of our initiators decide to quit valorant, so we are now looking for a dedicated player to join us in grinding ranked matches and aiming to reach Radiant soon.
Requirements:

- Minimum rank of Immortal 1 in the current or previous season
- Good communication skills and the ability to listen our in game leader calls
- Availability for regular practice sessions and ranked matches
- Positive attitude and a willingness to improve
- (optional)Well known sova and fade lineups

If you meet these requirements and feel confident in your skills, please feel free to direct message us.
\n
_[Optional attachment of profile/tracker/achievements/etc]_

        """

        await ctx.send(help_message)
    else:
        # Add custom help messages for specific commands if needed
        pass

@bot.command()
async def msg4(ctx, command=None):
    if command is None:
        help_message = """
## Hello <@&1214304917448298577> ,

We are excited to announce the 1st IBNT Valorant Cup! The tournament will start with a standard cup bracket for 8 teams. If we have 16 teams, we will switch to a Swiss system.
If there are more than 16 teams, a Swiss system followed by elimination rounds will be introduced to determine the top contenders.

> **Details:**
> 
> - Start Date: 7 days after the 8th team registration
> - Format:
>  - 8 Teams: Standard cup bracket
>  - 9-15 Teams: first 8 registered teams will participate
>  - 16 Teams: Swiss system
>  - 16+ Teams: Swiss system and elimination rounds
> - Registration Deadline: 5 days after the 8th team registration
> - Prizes: 100$

We look forward to your participation and to seeing some incredible gameplay. Get ready to compete and show your skills!

__Please register your team in <#1214311389385072641>__


*Best regards*       
        
        """

        await ctx.send(help_message)
    else:
        # Add custom help messages for specific commands if needed
        pass


@bot.command()
async def msg5(ctx, command=None):
    if command is None:
        help_message = """
# __REGISTRATION SHEET__  
**Team Tag:**  
**Team Name:**
**Captain(@HisDiscord):**
**Players:**
**TeamLogo(Optional)**:
**I have read all the #「:pushpin:」Rules and I accept them!**
        """
        await ctx.send(help_message)
    else:
        # Add custom help messages for specific commands if needed
        pass


@bot.command()
async def msg6(ctx, command=None):
    if command is None:
        help_message = """
# IBNT Valorant Cup rules
## §1 Overall Rules
All of the the「:pushpin:」rules apply.
## §2 Forfeit
If a team does not show up after 10 minutes after the captain has been contacted, the team is allowed to take the win by 13-0
A team forfeits, if the team cannot provide enough players anymore. You need only one player less than the maximum that can play at the same time to be able to play the tournament, for example in 5v5 you would only need 4 players to participate in a game.
## §3 Violation of rules
Please remember to follow all tournament rules. Breaking them, even accidentally, could mean warnings, point deductions, or disqualification. Know the rules well to play fair and avoid any penalties that could affect your team.
## §4 Registration
If you want to register a team, you need at least the minimum amount of players to have a full starting line-up. For example, in a 5v5 tournament, you would have to register 5 players to be accepted as registered, along with 2 reserves. Additionally, please note that the team logo is optional and must not be a square image; it must have a transparent background. Any changes to the registration after the registration phase has ended will result in individual penalties by the moderator team.
## §5 Games
All matches must be proceeded by the CX Valorant bot in <#1249849043614568509>.
Create a party, invite your friends and opponents, and then join the queue. After the match is finished, please remember that the leader of the losing team must report the loss to free all players from the lobby 

        """
        await ctx.send(help_message)
    else:
        # Add custom help messages for specific commands if needed
        pass


@bot.command()
async def msg61(ctx, command=None):
    if command is None:
        help_message = """
## §5.1 Standard bracket
When a game happens, the winning team will proceed to the next round, a team has to lose one time to fly out of the tournament.The maximum players on the team will be set by the tournament beforehand, that limit is not to be exceeded, if the limit is exceeded the team will receive an punishment discussed by the moderator team.
## §5.2 Swiss system
tournament format that ensures participants play a set number of rounds against opponents . Unlike single-elimination formats, players are not eliminated after a loss. Instead, they continue to compete, facing others with comparable performance, leading to a fair and balanced competition. This format is commonly used in chess, eSports, and various competitive events to rank participants efficiently and fairly.
## §6 Receipt of prize
To receive the prize, players must have either a Skrill or Wise account.
        """
        await ctx.send(help_message)
    else:
        # Add custom help messages for specific commands if needed
        pass


#delete app comands
# @bot.command(name='aideletecommands', aliases=['aidc'])
# async def delete_commands(ctx):
#     bot.tree.clear_commands(guild=None)
#     await bot.tree.sync()
#     await ctx.send('Commands deleted.')

# Run the bot with your token
bot.run('MTI0Mzk2MDA0MDUyNDYxMTYzNg.GvkvOW.Q--UDL0-2BhRd2ogzN5eujcFv5Zt_2zy7zdIyk')
