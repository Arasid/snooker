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

def stampNull2text(time):
    if time == 'NULL':
        return ''
    return stamp2text(time)

def get_days(times):
    days = {}
    years = set()
    for time in times:
        if time == 'NULL':
            continue
        dat = datetime.datetime.fromtimestamp(int(time))
        if dat.year < datetime.datetime.now().year - 4:
            continue
        day = (dat.year, dat.month, dat.day)
        years.add(dat.year)
        if not day in days:
            days[day] = 0
        days[day] += 1
    res = []
    for k,v in days.items():
        res.append([k[0],k[1],k[2],v])
    return res, len(years)

def winned(data):
    i = 0 if data['id1'] == data['me'] else 1
    if data['walkover'] > 0:
        return data['walkover'] == i+1
    scores = [data['score1'], data['score2']]
    return scores[i] > scores[1-i]

def get_seasons(seasonal):
    seasons = {}
    for data in seasonal:
        season = data['season']
        if season not in seasons:
            seasons[season] = {
                'winns': 0,
                'losses': 0
            }

        if winned(data):
            seasons[season]['winns'] += 1
        else:
            seasons[season]['losses'] += 1
    results = []
    for k,v in seasons.items():
        results.append((k,v['winns'],v['losses']))
    return sorted(results)


@app.route('/tournament/<id>/')
def tournament(id):
    cur = g.db.cursor()
    cur.execute('SELECT name,location,season,startdate,enddate,qualstartdate,qualenddate FROM tournaments WHERE id=?', (id,))
    tour = cur.fetchone()
    if tour is None:
        return render_template('error.html', msg=('Tournament ' + id + " doesn't exists."))
    info  = {
        'id': id,
        'name': tour[0],
        'location': tour[1],
        'season': tour[2],
        'startdate': stamp2text(tour[3]),
        'enddate': stamp2text(tour[4]),
        'qualstartdate': stampNull2text(tour[5]),
        'qualenddate': stampNull2text(tour[6]),
    }

    cur.execute('SELECT m.score1,m.score2,m.player1,m.player2,p1.name,p2.name,m.bestof,m.walkover,m.round FROM matches as m, players as p1, players as p2 WHERE m.round IN (SELECT id FROM rounds WHERE tournament = ?) AND m.player1 = p1.id AND m.player2 = p2.id ORDER BY round;', (id,))
    matches = cur.fetchall()
    cur.execute('SELECT id, name,roundorder FROM rounds WHERE tournament = ? ORDER BY roundorder ASC;', (id,))
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
    # lebo v DB su rounds naopak
    results = results[::-1]

    return render_template('tournament.html', info=info, results=results)

@app.route('/tournament/')
def tournaments():
    cur = g.db.cursor()
    return render_template('tournaments.html', tours=cur.execute('SELECT id, name FROM tournaments ORDER BY name DESC;'))

@app.route('/player/<id>/')
def player(id):
    id = int(id)
    cur = g.db.cursor()
    cur.execute('SELECT name, country, birthdate, professional FROM players WHERE id=?', (id,))
    player = cur.fetchone()
    if player is None:
        return render_template('error.html', msg=('Player ' + id + " doesn't exists."))
    info  = {
        'id': id,
        'name': player[0],
        'country': player[1],
        'birth': stamp2text(player[2]),
        'professional': player[3]
    }

    cur.execute('SELECT m.score1,m.score2,m.player1,m.player2,p1.name,p2.name,m.bestof,m.walkover,m.round, r.name, t.id, t.name,m.date,t.season FROM matches as m, players as p1, players as p2, rounds as r, tournaments as t WHERE m.player1 = p1.id AND m.player2 = p2.id AND m.round = r.id AND r.tournament = t.id AND (m.player1 = ? OR m.player2 = ?) ORDER BY t.name DESC;', (id, id))
    matches = cur.fetchall()
    cur.execute('SELECT id,name,roundorder FROM rounds WHERE tournament = ? ORDER BY roundorder ASC;', (id,))
    rounds = cur.fetchall()

    results = []
    last_tid = -1
    last_rid = -1
    times = []
    seasonal = []
    for score1, score2, id1, id2, player1, player2, bestof, walkover, round, round_name, t_id, t_name, date, season in matches:
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
        times.append(date)
        seasonal.append({
            'me': id,
            'id1': id1,
            'id2': id2,
            'score1': score1,
            'score2': score2,
            'walkover': walkover,
            'season': season
        })

    days,n_years = get_days(times)
    seasons = get_seasons(seasonal)

    cur.execute('SELECT t.startdate,t.name,e.rating FROM elo AS e, tournaments AS t WHERE e.tournament=t.id AND player=? ORDER BY t.startdate;', (id,))
    elos = []
    for time, name, rating in cur.fetchall():
        dat = datetime.datetime.fromtimestamp(int(time))
        day = (dat.year, dat.month, dat.day)
        elos.append({
            'name': name,
            'rating': rating,
            'date': day
        })

    return render_template('player.html', info=info, results=results, days=days, n_years=n_years, seasons=json.dumps(seasons), elos=json.dumps(elos))

@app.route('/player/')
def players():
    cur = g.db.cursor()
    return render_template('players.html', players=cur.execute('SELECT id, name FROM players ORDER BY name;'))

@app.route('/map/')
def map():
    cur = g.db.cursor()
    cur.execute('SELECT country,COUNT(*) FROM players GROUP BY country;')
    return render_template('map.html', players=json.dumps(cur.fetchall()))

@app.route('/')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8808, debug=True) 
