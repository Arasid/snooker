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
    cur.execute("SELECT name FROM tournaments WHERE id=?", (id,))
    tour = cur.fetchone()
    if tour is None:
        return render_template('error.html', msg=("Tournament " + id + " doesn't exists."))
    info  = {
        'id': id,
        'name': tour[0],
    }

    return render_template('tournament.html', info=info)

@app.route('/tournament/')
def tournaments():
    cur = g.db.cursor()
    return render_template('tournaments.html', tours=cur.execute("SELECT id, name FROM tournaments ORDER BY name DESC;"))

@app.route('/player/<id>/')
def player(id):
    cur = g.db.cursor()
    cur.execute("SELECT name, country, birthdate FROM players WHERE id=?", (id,))
    player = cur.fetchone()
    if player is None:
        return render_template('error.html', msg=("Player " + id + " doesn't exists."))
    info  = {
        'id': id,
        'name': player[0],
        'country': player[1],
        'birth': stamp2text(player[2])
    }

    return render_template('player.html', info=info)

@app.route('/player/')
def players():
    cur = g.db.cursor()
    return render_template('players.html', players=cur.execute("SELECT id, name FROM players ORDER BY name;"))

@app.route('/')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8808, debug=True) 
