from bs4 import BeautifulSoup
import urllib2
import time
import datetime
import re
import sqlite3
import sys
import create_db

# parameters
years = [2016]
category = 'Ranking'
category_col_name = 'Category'
status = 'Professional'
status_col_name = 'Status'
tour_col_name = 'Tournament'

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

def parse_dates(text):
    res = []
    for x in text.split('-'):
        date = re.sub(r'(\d)(st|nd|rd|th)', r'\1', x.strip())
        date = time.mktime(datetime.datetime.strptime(date, "%B %d %Y").timetuple())
        res.append(date)
    return res

def crawl_tour(tour_url, title):
    print "crawling Tournament: %s" % title
    f = urllib2.urlopen(tour_url)
    time.sleep(1)
    html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    x = soup.find("td", text="Dates: ")
    dates = x.find_next_sibling().text
    start, end = parse_dates(dates)
    x = soup.find("td", text="Location: ")
    location = x.find_next_sibling().text
    c.execute("INSERT INTO tournaments(id, name, location, startdate, enddate) VALUES (NULL, ?, ?, ?, ?)", (title, location, start, end))
    conn.commit()

def crawl_year(year):
    year_url = 'http://cuetracker.net/Tournaments/%s' % year
    f = urllib2.urlopen(year_url)
    time.sleep(1)
    print "crawling YEAR", year_url
    html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    f = soup.select_one("#main_table")
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
        tours.append((url, tds[tour_col].text.strip()))

    for tour, title in tours:
        crawl_tour(tour, title)

for year in years:
    crawl_year(year)

conn.close()
