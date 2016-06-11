import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS players (
                id integer primary key,
                name text,
                birthdate integer,
                country text,
                professional text)''')
c.execute('''CREATE TABLE IF NOT EXISTS tournaments (
                id integer primary key,
                name text,
                location text,
                startdate integer,
                enddate integer,
                qualstartdate integer,
                qualenddate integer )''')
c.execute('''CREATE TABLE IF NOT EXISTS rounds (
                id integer primary key,
                name text,
                roundorder integer,
                tournament integer,
                FOREIGN KEY(tournament) REFERENCES tournaments(id) )''')
c.execute('''CREATE TABLE IF NOT EXISTS matches (
                id integer primary key,
                score1 integer,
                score2 integer,
                date integer, 
                round integer,
                player1 integer,
                player2 integer,
                bestof integer,
                walkover integer,
                frames text,
                FOREIGN KEY(round) REFERENCES rounds(id),
                FOREIGN KEY(player1) REFERENCES players(id),
                FOREIGN KEY(player2) REFERENCES players(id) )''')

conn.commit()
conn.close()
