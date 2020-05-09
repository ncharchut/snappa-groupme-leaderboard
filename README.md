# Snappa Leaderboard GroupMe Bot
GroupMe bot for maintaining ELO rankings for snappa/dye matchplay.

Our beloved game, like most, has always possessed a notion of who is the best.
Single matches, tournaments, surely enough games have been played to effectively say
who (or what team) is the best. That's where this bot comes in.

## Usage
Once deployed in your groupchat of choice, record a game with the following syntax.
For 2 v. 2 games,

`/score @player1 @player2 @player3 @player4 , SCORE_12 - SCORE_34`

where `SCORE_12` is the score of the team of players 1 and 2, and `SCORE_34`
is the score of the team of players 3 and 4.

For 1 v. 1 games (though this currently is not a functionality),

`/score @player1 @player2, SCORE_1 - SCORE_2`

To see the leaderboard, simply chat, `/leaderboard` or `/lb`. Don't be the
person who checks rankings after every game. Have to keep that chat *_clean_*.

## Todo
- [x] Score/input validation.
- [x] Set up Postgres database and record matches using the above command.
- [x] Add admin functionality to strike games from the record.
- [x] Additional functionalities (e.g. mugs/sinks per game)
- [ ] Scripts
  - [ ] Script for pushing/defining any remaining configuration variables.
  - [ ] Script that does all of the above in one go.
- [ ] Update README with how to deploy easily.

## Setup Locally
1. Clone/fork this repository. If cloning/messing around with it, *be sure to push to your GitHub account*.
2. Setup a Heroku account [here](https://signup.heroku.com/login).
3. Create a new Heroku app with whatever app name you'd like (ideal if it's SFW because this is public-facing).
4. Add the *Heroku Postgres* Add-on (free) and make sure your Dyno Type includes `web gunicorn app:app --log-file=-`
5. Create a GroupMe bot using the [official website](https://dev.groupme.com/). You may need to create a developer account. Note both the **BOT ID** and **GROUP ID**, you will need these.
