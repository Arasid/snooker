from bs4 import BeautifulSoup
import urllib2
import time
import datetime
import re
import sqlite3
import sys
import json

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS predict (
                id integer primary key,
                tournament integer,
                matches text,
                FOREIGN KEY(tournament) REFERENCES tournaments(id) )''')

def get_player(text):
    g = re.match(r'Winner of Match (\d+)', text)
    if g is None:
        return text
    return g.group(1)

matches = []
def crawl_tour(tour_url, title):
    print 'crawling Tournament: %s' % title
    c.execute('SELECT id from tournaments WHERE name=?;', (title,))
    id = int(c.fetchone()[0])
    f = urllib2.urlopen(tour_url)
    #time.sleep(1)
    html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    round = 1
    while True:
        x = soup.select_one('table#round%d'%round)
        if x is None:
            break

        rows = x.select('tr')
        for row in rows:
            tds = row.select('td')
            if len(tds) == 0: continue
            player1 = get_player(tds[1].getText(strip=True))
            player2 = get_player(tds[3].getText(strip=True))
            matches.append({
                'id': tds[0].getText(strip=True),
                'player1': player1,
                'player2': player2
            })
        round += 1
    c.execute('DELETE FROM predict WHERE tournament=?', (id,))
    c.execute('INSERT INTO predict(id, tournament, matches) VALUES (NULL, ?, ?)', (id, json.dumps(matches)))

crawl_tour('http://livescores.worldsnookerdata.com/Matches/Index/13902/kaspersky-riga-masters', '2016 Riga Masters')
crawl_tour('http://livescores.worldsnookerdata.com/Matches/Index/13898/indian-open', '2016 Indian Open')
conn.commit()
conn.close()
