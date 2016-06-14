import time
import numpy as np
import datetime
import sqlite3
import sys

prof_const = 400
amat_const = 200

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
c.execute('drop table if exists elo')
c.execute('''CREATE TABLE elo (
                id integer primary key,
                player integer,
                tournament integer,
                rating number,
                FOREIGN KEY(player) REFERENCES players(id),
                FOREIGN KEY(tournament) REFERENCES tournaments(id) )''')

def winned(score1, score2, walkover):
    res = [0, 0]
    if walkover > 0:
        res[walkover-1] = 1
    else:
        if score1 > score2:
            res[0] = 1
        else:
            res[1] = 1
    return res

c.execute('SELECT id, professional FROM players;')
professional = {}
for id, prof in c.fetchall():
    if prof == 'Never':
        continue
    professional[id] = int(prof)

ratings = {}
def get_rating(id, year):
    if id not in ratings:
        if id in professional and professional[id] <= year:
            ratings[id] = prof_const
        else:
            ratings[id] = amat_const
    return ratings[id]

def k_factor(id, year):
    if id in professional and professional[id] <= year:
        return 16
    return 32

def season_first_year(season):
    f,s = season.split('-')
    return int(f)

c.execute('SELECT t.id,t.season,t.name FROM tournaments AS t, rounds AS r, matches AS m WHERE r.tournament=t.id AND m.round=r.id AND r.roundorder=(SELECT MAX(roundorder) FROM rounds WHERE tournament = t.id) GROUP BY t.id HAVING COUNT(m.id)==1 ORDER BY t.startdate;')
tours = [(int(x[0]),season_first_year(x[1]),x[2]) for x in c.fetchall()]

# vypocitam nove rating pre kazdeho do new_rating, a tie zapisem ze ake su po tournamente
# nerobim to kazdemu, iba tomu co sutazili
# tympadom na konci len rating updatnem
for tour,season,name in tours:
    print 'Tournament id: %s' % name
    c.execute('SELECT id FROM rounds WHERE tournament=? ORDER BY roundorder DESC LIMIT 5', (tour,))
    rounds = [int(x[0]) for x in c.fetchall()]
    new_ratings = {}
    for round in rounds[::-1]:
        c.execute('SELECT player1, player2, score1, score2, walkover FROM matches WHERE round=?', (round,))
        matches = c.fetchall()
        for player1, player2, score1, score2, walkover in matches:
            win = winned(score1, score2, walkover)
            players = [player1, player2]
            rs = [get_rating(id, season) for id in players]
            qs = [10**(r/400.0) for r in rs]
            es = [q/sum(qs) for q in qs]
            ks = [k_factor(id, season) for id in players]
            for i in range(2):
                new_r = rs[i] + ks[i]*(win[i]-es[i])
                new_ratings[players[i]] = new_r
                ratings[players[i]] = new_r
    for id, rating in new_ratings.items():
        c.execute('INSERT INTO elo(id, player, tournament, rating) VALUES (NULL, ?, ?, ?)', (id, tour, rating))
    conn.commit()
conn.close()
