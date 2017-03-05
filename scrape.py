import yaml
import requests
from bs4 import BeautifulSoup as BS
import betamax
from attr import attrs, attrib
import logging
import sys

import pdb

BOARD_URL = sys.argv[1]

logging.basicConfig(level=logging.INFO)

@attrs
class Category():
    id = attrib(convert=int)
    url = attrib()
    name = attrib()

@attrs
class Forum():
    id = attrib(convert=int)
    url = attrib()
    category_id = attrib()
    name = attrib()
    description = attrib()
    type = attrib()
    num_topics = attrib(convert=int)
    num_replies = attrib(convert=int)

class ZetaboardsScraper():
    def __init__(self, board_url):
        self.board_url = board_url
        self.categories = None
        
    def scrape_front(self):
        s = requests.Session()

        r = s.get(BOARD_URL)
        soup = BS(r.text, 'html.parser')
        
        a = soup.find('div', id='wrap').a
        self.board_name = a.text.strip()
        logging.info("Board name: {}".format(self.board_name))
        assert a['href'] == self.board_url

        self.categories = []
        self.fora = []

        for div in soup.find_all('div', class_="category"):
            if div['id'] == "stats": continue
            
            h2 = soup.find('h2')
            
            category = Category(
                url = h2.a['href'],
                name = h2.text.strip(),
                id = div['id'].split('-')[1]
            )
            self.categories.append(category)
            
            for tr_forum in div.find_all('tr', class_="forum"):
                td_mark, td_forum, td_last = tr_forum.find_all('td')
                td_viewers, td_topics, td_replies = tr_forum.next_sibling.next_sibling.find_all('td')
            
                forum = Forum(
                    id = tr_forum['id'].split('-')[1],
                    category_id = category.id,
                    url = td_forum.a['href'],
                    name = td_forum.a.text.strip(),
                    description = td_forum.div.text.strip(),
                    type = td_mark.img['alt'],
                    num_topics = td_topics.text.split()[-1],
                    num_replies = td_replies.text.split()[-1],
                )
                self.fora.append(forum)
    
        logging.info("Categories ({}): {}".format(len(self.categories), "; ".join(c.name for c in self.categories)))
        logging.info("Fora ({}): {}".format(len(self.fora), "; ".join(f.name for f in self.fora)))


zs = ZetaboardsScraper(BOARD_URL)
zs.scrape_front()
