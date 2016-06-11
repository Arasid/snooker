from bs4 import BeautifulSoup
import urllib2
import time
import datetime
import re
import sqlite3
import sys
import create_db

# parameters
years = [2016, 2015, 2014, 2013, 2012, 2011, 2010, 2009, 2008, 2007]
category = 'Ranking'
category_col_name = 'Category'
status = 'Professional'
status_col_name = 'Status'
tour_col_name = 'Tournament'

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

def get_date(text):
    return time.mktime(datetime.datetime.strptime(text, '%Y-%m-%d').timetuple())

def parse_eng_date(text):
    if text == 'Unavailable':
        return -1
    date = re.sub(r'(\d)(st|nd|rd|th)', r'\1', text.strip())
    return time.mktime(datetime.datetime.strptime(date, '%B %d %Y').timetuple())

def parse_dates(text):
    res = []
    for x in text.split('-'):
        res.append(parse_eng_date(x))
    if len(res) == 1:
        res.append(res[-1])
    return res

def get_player(td):
    name = td.getText(strip=True)
    c.execute('SELECT id FROM players WHERE name=?', (name,))
    player = c.fetchone()
    if player is None:
        print 'Crawling player: %s' % name
        # create player
        url = td['href']
        f = urllib2.urlopen(url)
        time.sleep(1)
        html = f.read()
        soup = BeautifulSoup(html, 'html.parser')
        th = soup.find('th', text='Player Information')
        tbody = th.find_parent().find_parent().select_one('tbody')
        country = tbody.find('td', text='Country').find_next_sibling().getText(strip=True)
        professional_year = tbody.find('td', text='Turned professional').find_next_sibling().getText(strip=True)
        birth = tbody.find('td', text='Date of birth').find_next_sibling().getText(strip=True)
        birth = parse_eng_date(' '.join(birth.split()[:3]))
        c.execute('INSERT INTO players(id, name, birthdate, country, professional) VALUES (NULL, ?, ?, ?, ?)',
                        (name, birth, country, professional_year))
        return c.lastrowid
    else:
        return player[0]

def crawl_round(round_id, round_tds):
    print 'crawling Round: %s' % round_id
    for round_td in round_tds:
        row = round_td.find_parent()
        player1_td = row.select_one('td.match_player1 a')
        player2_td = row.select_one('td.match_player2 a')
        player1 = get_player(player1_td)
        player2 = get_player(player2_td)
        player1_score = row.select_one('td.match_player1_score').getText(strip=True)
        player2_score = row.select_one('td.match_player2_score').getText(strip=True)
        bestof = row.select_one('td.match_best_of').getText(strip=True)
        # su tam () kolo cisla (asi vzdy, im not sure)
        bestof = re.match(r'[\(]?(\d*)[\)]?', bestof).group(1)

        x = re.compile('.*(Walkover).*')
        walkover = 0
        for i in [1,2]:
            walk = row.select_one('td.match_player%s' % i).getText(strip=True)
            res = x.match(walk)
            if res is not None:
                walkover = i

        date = 'NULL'
        frames = ''
        if walkover == 0:
            next_row = row.find_next_sibling()
            if next_row.select_one('td.match_round') is None:
                td = next_row.select_one('td')
                date_text = td.getText('|||', strip=True)
                if date_text != "":
                    date_text = date_text.split('|||')[1]
                    # ak je tam range, tak zatial na nho kaslem ... lebo ani nie je pri vsetkych zapasoch
                    # pri ktorych by mal byt
                    date_text = date_text.split(' - ')[0]
                    date = get_date(date_text)

                frames = td.find_next_sibling().getText('|||', strip=True)
                if frames != '':
                    frames = frames.split('|||')[1]

        c.execute('''
                    INSERT INTO matches(id, score1, score2, date, round, player1, player2, bestof, walkover, frames)
                    VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                    (player1_score, player2_score, date, round_id, player1, player2, bestof, walkover, frames))

def crawl_tour(tour_url, title):
    print 'crawling Tournament: %s' % title
    f = urllib2.urlopen(tour_url)
    time.sleep(1)
    html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    x = soup.find('td', text='Dates: ')
    dates = x.find_next_sibling().text
    start, end = parse_dates(dates)
    x = soup.find('td', text='Qualifying dates: ')
    dates = x.find_next_sibling().text
    qstart, qend = 'NULL', 'NULL'
    if dates != 'No qualifier dates available':
        qstart, qend = parse_dates(dates)
    x = soup.find('td', text='Location: ')
    location = x.find_next_sibling().text
    c.execute('''INSERT INTO tournaments(id, name, location, startdate, enddate, qualstartdate, qualenddate) 
                VALUES (NULL, ?, ?, ?, ?, ?, ?)''', (title, location, start, end, qstart, qend))
    tour_id = c.lastrowid
    conn.commit()

    tds = soup.select('td.match_round')
    rounds = []
    rounds_tds = []
    for td in tds:
        title = td.text
        if len(rounds) == 0 or rounds[-1] != title:
            rounds.append(title)
            rounds_tds.append([])
        rounds_tds[-1].append(td)
    for i in range(len(rounds)):
        c.execute('INSERT INTO rounds(id, name, roundorder, tournament) VALUES (NULL, ?, ?, ?)', (rounds[i], i, tour_id))
        round_id = c.lastrowid
        crawl_round(round_id, rounds_tds[i])
        conn.commit()

def crawl_year(year):
    year_url = 'http://cuetracker.net/Tournaments/%s' % year
    f = urllib2.urlopen(year_url)
    time.sleep(1)
    print 'crawling YEAR', year_url
    html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    f = soup.select_one('#main_table')
    ## aby som vedela ze ktory stlpec co znamena
    col_names = [x.text for x in f.select('thead > th')]
    tour_col = col_names.index(tour_col_name)
    cat_col = col_names.index(category_col_name)
    status_col = col_names.index(status_col_name)

    tours = []
    rows = f.select('tbody > tr')
    for row in rows:
        url = None
        tds = row.select('td')

        # chcem len konkretnu kategoriu
        if tds[cat_col].text != category:
            continue
        # a konkretny status
        if tds[status_col].text != status:
            continue
        url = tds[tour_col].select_one('a').get('href')
        tours.append((url, tds[tour_col].getText(strip=True)))

    for tour, title in tours:
        crawl_tour(tour, title)

for year in years:
    crawl_year(year)

conn.commit()
conn.close()
