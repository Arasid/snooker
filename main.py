from flask import Flask, render_template, g
import sqlite3
import datetime
import json
from sklearn.feature_extraction.text import CountVectorizer

app = Flask(__name__)

def connect_db():
    return sqlite3.connect('db.sqlite3')

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

def stamp2text(time):
    return datetime.datetime.fromtimestamp(int(time)).strftime('%d.%m.%Y')

#def get_days(times):
#    days = {}
#    for time in times:
#        dat = datetime.datetime.fromtimestamp(int(time))
#        day = (dat.year, dat.month, dat.day)
#        if not day in days:
#            days[day] = 0
#        days[day] += 1
#    res = []
#    for k,v in days.items():
#        res.append([k[0],k[1],k[2],v])
#    return res

@app.route('/tournament/<id>/')
def tournament(id):
    cur = g.db.cursor()
    cur.execute("SELECT name,location,startdate,enddate,qualstartdate,qualenddate FROM tournaments WHERE id=?", (id,))
    tour = cur.fetchone()
    if tour is None:
        return render_template('error.html', msg=("Tournament " + id + " doesn't exists."))
    info  = {
        'id': id,
        'name': tour[0],
        'location': tour[1],
        'startdate': stamp2text(tour[2]),
        'enddate': stamp2text(tour[3]),
        'qualstartdate': "" if tour[4] == 'NULL' else stamp2text(tour[4]),
        'qualenddate': "" if tour[5] == 'NULL' else stamp2text(tour[5]),
    }

    cur.execute("SELECT m.score1,m.score2,m.player1,m.player2,p1.name,p2.name,m.bestof,m.walkover,m.round FROM matches as m, players as p1, players as p2 WHERE m.round IN (SELECT id FROM rounds WHERE tournament = ?) AND m.player1 = p1.id AND m.player2 = p2.id ORDER BY round;", (id,))
    matches = cur.fetchall()
    cur.execute("SELECT id, name,roundorder FROM rounds WHERE tournament = ? ORDER BY roundorder ASC;", (id,))
    rounds = cur.fetchall()

    results = []
    r_map = {}
    for id, name, order in rounds:
        results.append({
            'name': name,
            'matches': []
        })
        r_map[id] = order
    for score1, score2, id1, id2, player1, player2, bestof, walkover, round in matches:
        round_o = r_map[round]
        results[round_o]['matches'].append({
            'score1': score1,
            'score2': score2,
            'id1': id1,
            'id2': id2,
            'player1': player1,
            'player2': player2,
            'bestof': bestof,
            'walkover': walkover
        })

    return render_template('tournament.html', info=info, results=results)

@app.route('/tournament/')
def tournaments():
    cur = g.db.cursor()
    return render_template('tournaments.html', tours=cur.execute("SELECT id, name FROM tournaments ORDER BY name DESC;"))

@app.route('/player/<id>/')
def player(id):
    cur = g.db.cursor()
    cur.execute("SELECT name, country, birthdate, professional FROM players WHERE id=?", (id,))
    player = cur.fetchone()
    if player is None:
        return render_template('error.html', msg=("Player " + id + " doesn't exists."))
    info  = {
        'id': id,
        'name': player[0],
        'country': player[1],
        'birth': stamp2text(player[2]),
        'professional': player[3]
    }

    cur.execute('SELECT m.score1,m.score2,m.player1,m.player2,p1.name,p2.name,m.bestof,m.walkover,m.round, r.name, t.id, t.name FROM matches as m, players as p1, players as p2, rounds as r, tournaments as t WHERE m.player1 = p1.id AND m.player2 = p2.id AND m.round = r.id AND r.tournament = t.id AND (m.player1 = ? OR m.player2 = ?) ORDER BY t.name DESC;', (id, id))
    matches = cur.fetchall()
    cur.execute("SELECT id,name,roundorder FROM rounds WHERE tournament = ? ORDER BY roundorder ASC;", (id,))
    rounds = cur.fetchall()

    results = []
    last_tid = -1
    last_rid = -1
    for score1, score2, id1, id2, player1, player2, bestof, walkover, round, round_name, t_id, t_name in matches:
        if t_id != last_tid:
            last_tid = t_id
            results.append({
                'name': t_name,
                'id': t_id,
                'rounds': []
            })
            last_rid =-1
        if round != last_rid:
            results[-1]['rounds'].append({
                'name': round_name,
                'matches': []
            })

        results[-1]['rounds'][-1]['matches'].append({
            'score1': score1,
            'score2': score2,
            'id1': id1,
            'id2': id2,
            'player1': player1,
            'player2': player2,
            'bestof': bestof,
            'walkover': walkover
        })

    return render_template('player.html', info=info, results=results)

@app.route('/player/')
def players():
    cur = g.db.cursor()
    return render_template('players.html', players=cur.execute("SELECT id, name FROM players ORDER BY name;"))

@app.route('/')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8808, debug=True) 
