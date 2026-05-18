# 🎮 CX Valorant Bot

A Discord bot for organizing **5v5 Valorant scrim matches** on your server. Supports party management, matchmaking queues, map bans, win tracking, and a leaderboard — all via slash commands.

---

## ✨ Features

- **Party System** — Create parties, invite players, merge parties, force-add members
- **Matchmaking Queue** — Parties of 5 or 10 join a queue; match starts automatically when 10 players are ready
- **Map Ban Phase** — Interactive map voting with all current Valorant maps (Bind, Haven, Split, Ascent, Icebox, Breeze, Fracture, Pearl, Lotus, Sunset, Abyss)
- **Lobby Management** — After a match starts, players are placed in a lobby; the losing team's leader reports the result
- **Win & Stats Tracking** — Wins and games played are persisted across restarts
- **Leaderboard** — Top 10 players ranked by wins
- **Abort System** — Both team leaders can vote to abort a match
- **Template Messages** — Ready-made Discord post templates for LFP/LFT announcements and tournament rules

---

## 📋 Commands

### Party Management

| Command | Parameters | Description |
|---|---|---|
| `/create_party` | `name` | Create a new party |
| `/invite_user` | `party_name`, `username` | Invite a user to your party |
| `/accept` | `party_name` | Accept a party invitation |
| `/merge_party` | `party_name` | Send a merge request to another party |
| `/confirm_merge` | — | Accept an incoming merge request |
| `/show_party` | `name` (optional) | Show members of a party |
| `/party_leave` | — | Leave your current party |
| `/party_remove` | `username` | Remove a member from your party (leader only) |
| `/force` | `username` | Forcefully add a player to your party (leader only) |

### Queue & Matchmaking

| Command | Parameters | Description |
|---|---|---|
| `/join_queue` | — | Join the queue with your party (5 or 10 members required) |
| `/leave_queue` | — | Leave the queue with your party |
| `/queue` | — | Show current queue status |

### In-Game

| Command | Parameters | Description |
|---|---|---|
| `/lobby` | — | Display current lobby members and team assignments |
| `/report_loss` | — | Report your team's loss and close the lobby |
| `/abort` | — | Vote to abort the current match (both leaders must agree) |
| `/maps` | — | Display available maps |

### Stats & Leaderboard

| Command | Parameters | Description |
|---|---|---|
| `/stats` | `username` (optional) | View wins and win rate for a player |
| `/wins` | — | Show the top 10 players leaderboard |

---

## 🔧 Setup

### Requirements

- Python 3.10+
- [disnake](https://github.com/DisnakeDev/disnake) library


## 📁 Data Storage

The bot stores player statistics in plain text files in the working directory:

- `user_wins.txt` — win counts per user ID
- `user_games.txt` — games played per user ID

Both files are loaded on startup and updated after every reported match result.

---

## 🗺️ Supported Maps

Bind · Haven · Split · Ascent · Icebox · Breeze · Fracture · Pearl · Lotus · Sunset · Abyss

