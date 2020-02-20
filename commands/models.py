from database import db


class Score(db.Model):
    """ Schema for score submission for a given match. """
    __tablename__ = 'records'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)

    # Player id's.
    player_1 = db.Column(db.String())
    player_2 = db.Column(db.String())
    player_3 = db.Column(db.String())
    player_4 = db.Column(db.String())

    # Team scores.
    score_12 = db.Column(db.Integer)
    score_34 = db.Column(db.Integer)

    # Points for all players.
    points_1 = db.Column(db.Integer)
    points_2 = db.Column(db.Integer)
    points_3 = db.Column(db.Integer)
    points_4 = db.Column(db.Integer)

    # Sinks per player.
    sinks_1 = db.Column(db.Integer)
    sinks_2 = db.Column(db.Integer)
    sinks_3 = db.Column(db.Integer)
    sinks_4 = db.Column(db.Integer)

    # Timestamp for the match.
    timestamp = db.Column(db.Integer)

    # Rank per player (BEFORE the match).
    elo_1 = db.Column(db.Integer, default=1000)
    elo_2 = db.Column(db.Integer, default=1000)
    elo_3 = db.Column(db.Integer, default=1000)
    elo_4 = db.Column(db.Integer, default=1000)

    def __init__(self, player_1, player_2, player_3, player_4,
                 score_12, score_34, points, sinks, timestamp,
                 elo_1, elo_2, elo_3, elo_4):
        self.player_1 = player_1
        self.player_2 = player_2
        self.player_3 = player_3
        self.player_4 = player_4
        self.points_1, self.points_2, self.points_3, self.points_4 = points
        self.sinks_1, self.sinks_2, self.sinks_3, self.sinks_4 = sinks
        self.timestamp = timestamp

        self.score_12 = score_12
        self.score_34 = score_34
        self.elo_1 = elo_1
        self.elo_2 = elo_2
        self.elo_3 = elo_3
        self.elo_4 = elo_4

    def __repr__(self):
        return (f"<id {self.id} | {self.player_1} | {self.player_2}"
                f" | {self.player_3} | {self.player_4} |"
                f"{self.score_12} | {self.score_34}\n"
                f"{self.elo_1} | {self.elo_2} | {self.elo_3} | {self.elo_4}")

    def __team_of_two(self, team):
        """ Will be used when database supports 1 v. 1 matches. """
        return isinstance(team, list) or isinstance(team, tuple)


class Stats(db.Model):
    """ Schema for people and rankings. """
    __tablename__ = 'stats'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)

    # Player information.
    player_id = db.Column(db.String())
    name = db.Column(db.String())
    elo = db.Column(db.Integer, default=1000)

    # Career stats.
    games = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    sinks = db.Column(db.Integer, default=0)

    def __init__(self, player_id, name):
        self.player_id = player_id
        self.name = name

    def __repr__(self):
        return (f"{self.name} | {self.elo} | {self.wins} | "
                f"{self.losses} | {self.games} | {self.points} | "
                f"{self.sinks}")
