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
    category_id = attrib(convert=int)
    name = attrib()
    description = attrib()
    type = attrib()
    num_topics = attrib(convert=int)
    num_replies = attrib(convert=int)

@attrs
class topic():
    id = attrib(convert=int)
    url = attrib()
    forum_id = attrib(convert=int)
    title = attrib()
    description = attrib()
    tags = attrib()
    pinned = attrib()
    start_date = attrib()
    starter_id = attrib(convert=int)
    num_replies = attrib(convert=int)
    num_views = attrib(convert=int)

class ZetaboardsScraper():
    def __init__(self, board_url):
        self.board_url = board_url
        self.categories = None
        self.fora = None
        self.topics = []
        
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
            if div['id'] in ("stats", "sbx"): continue
            
            h2 = soup.find('h2')
            
            category = Category(
                url  = h2.a['href'],
                name = h2.text.strip(),
                id   = div['id'].split('-')[1]
            )
            self.categories.append(category)
            
            for tr_forum in div.find_all('tr', class_="forum"):
                td_mark, td_forum, td_last = tr_forum.find_all('td')
                td_viewers, td_topics, td_replies = tr_forum.next_sibling.next_sibling.find_all('td')
            
                forum = Forum(
                    id          = tr_forum['id'].split('-')[1],
                    category_id = category.id,
                    url         = td_forum.a['href'],
                    name        = td_forum.a.text.strip(),
                    description = td_forum.div.text.strip(),
                    type        = td_mark.img['alt'],
                    num_topics  = td_topics.text.split()[-1].replace(',', ''),
                    num_replies = td_replies.text.split()[-1].replace(',', ''),
                )
                self.fora.append(forum)
    
        logging.info("Categories ({}): {}".format(len(self.categories), "; ".join(c.name for c in self.categories)))
        logging.info("Fora ({}): {}".format(len(self.fora), "; ".join(f.name for f in self.fora)))
    
    def scrape_forum_page(self, forum, page):
        r = requests.get("{}{}/".format(forum.url, page))
        soup = BS(r.text, 'html.parser')
        
        topics = []
        
        for tr in soup.find('table', class_='posts').find_all('tr'):
            if 'class' not in tr.attrs: continue
            # the page list is only in the way
            ul_pages = tr.find(class_='c_cat-title').find('ul', class_='cat-topicpages')
            if ul_pages:
                ul_pages.decompose()
            topic = topic(
                id          = tr.find(class_='c_cat-title').a['href'].split('/')[-2],
                url         = tr.find(class_='c_cat-title').a['href'],
                forum_id    = forum.id,
                title       = tr.find(class_='c_cat-title').a.text.strip(),
                description = tr.find(class_='description').text.strip(),
                tags        = None,
                pinned      = tr.find(class_='c_cat-title').text.startswith("Pinned:"),
                start_date  = tr.find(class_='c_cat-title').a['title'], # XXX
                starter_id  = tr.find(class_='c_cat-starter').a['href'].split('/')[-2],
                num_replies = tr.find(class_='c_cat-replies').text.replace(',', ''),
                num_views   = tr.find(class_='c_cat-views').text.split()[0].replace(',', '')
            )
            print(topic)
            
            topics.append(topic)
        
        return topics
    
    def scrape_forum(self, forum):
        r = s.get(forum.url)
        soup = BS(r.text, 'html.parser')
        
        ul_pages = soup.find('ul', class_='cat-pages')
        last_page = int(soup.find_all('li')[-1].a.text.strip())
        


zs = ZetaboardsScraper(BOARD_URL)
zs.scrape_front()

print(zs.fora[0])
zs.scrape_forum_page(zs.fora[0], 1)
print(zs.topics)

