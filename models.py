def create_score_data_object(db):
    class Score(db.Model):
        """ Schema for score submission for a given match. """
        __tablename__ = 'snappa-scores'

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

        def __init__(self, player_1, player_2, player_3, player_4,
                     score_12, score_34, points, sinks, timestamp):
            self.player_1 = player_1
            self.player_2 = player_2
            self.player_3 = player_3
            self.player_4 = player_4
            self.points_1, self.points_2, self.points_3, self.points_4 = points
            self.sinks_1, self.sinks_2, self.sinks_3, self.sinks_4 = sinks
            self.score_12 = score_12
            self.score_34 = score_34
            self.timestamp = timestamp

        def __repr__(self):
            return f"<id {self.id}>"

        def __team_of_two(self, team):
            """ Will be used when database supports 1 v. 1 matches. """
            return isinstance(team, list) or isinstance(team, tuple)
    return Score


def create_rank_data_object(db):
    class Rank(db.Model):
        """ Schema for people and rankings. """
        __tablename__ = 'rankings'
        id = db.Column(db.Integer, primary_key=True)

        # Player information.
        player_id = db.Column(db.String())
        name = db.Column(db.String())
        rank = db.Column(db.Integer)

        # Career stats.
        games = db.Column(db.Integer, default=0)
        wins = db.Column(db.Integer, default=0)
        losses = db.Column(db.Integer, default=0)
        points = db.Column(db.Integer, default=0)
        sinks = db.Column(db.Integer, default=0)

        def __init__(self, player_id, name, initial_rank):
            self.player_id = player_id
            self.name = name
            self.rank = initial_rank

        def __repr__(self):
            return f"<id {self.id}>"
    return Rank
