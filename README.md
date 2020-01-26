# Snappa Leaderboard GroupMe Bot
GroupMe bot for maintaining ELO rankings for snappa/dye matchplay.

Our beloved game, like most, has always possessed a notion of who is the best.
Single matches, tournaments, surely enough games have been played to effectively say
who (or what team) is the best. That's where this bot comes in.

## Usage
Once deployed in your groupchat of choice, record a game with the following syntax.
For 2 v. 2 games,

`/score @player1 @player2 @player3 @player4 SCORE_12 - SCORE_34`

where `SCORE_12` is the score of the team of players 1 and 2, and `SCORE_34`
is the score of the team of players 3 and 4.

For 1 v. 1 games,

`/score @player1 @player2 SCORE_1 - SCORE_2`

To see the leaderboard, simply chat, `/rankings`. Don't be the
person who checks rankings after every game. Have to keep that chat _clean_.

## Todo
- [x] Score/input validation.
- [ ] Set up Postgres database and record matches using the above command.
- [ ] Add admin functionality to strike games from the record.
- [x] Additional functionalities (e.g. mugs/sinks per game)
- [ ] Update README with how to deploy easily.
