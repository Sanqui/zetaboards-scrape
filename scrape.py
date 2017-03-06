import yaml
import requests
from bs4 import BeautifulSoup as BS
import betamax
from attr import attrs, attrib
import logging
import sys
from datetime import datetime
from pprint import pprint

from pdb import set_trace as bp

import config

board_url = config.BOARD_URL

CASSETTE_LIBRARY_DIR = 'cassettes/'
CASSETTE_NAME = None

DATETIME_FORMAT = "%b %d %Y, %I:%M %p"

logging.basicConfig(level=logging.INFO)

class FailedToLogInError(Exception): pass

@attrs
class Category():
    id = attrib(convert=int)
    url = attrib()
    name = attrib()
    
    def __str__(self):
        return "Category({}, {})".format(self.id, self.name)

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
    
    def __str__(self):
        return "Forum({}, {})".format(self.id, self.name)

@attrs
class Topic():
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
    
    def __str__(self):
        return "Topic({}, {})".format(self.id, self.title)

@attrs
class Post():
    id = attrib(convert=int)
    url = attrib()
    edit_url = attrib()
    topic_id = attrib()
    user_id = attrib()
    number = attrib()
    post_datetime = attrib()
    ip = attrib()
    post_html = attrib()
    
    def __str__(self):
        return "Post({}, {}...)".format(self.id, self.post_html[0:20])

def get_last_page(soup):
    ul_pages = soup.find('ul', class_='cat-pages')
    if ul_pages:
        last_page = int(soup.find_all('li')[-1].text.strip())
    else:
        last_page = 1
    
    return last_page

class ZetaboardsScraper():
    def __init__(self, board_url):
        self.board_url = board_url
        assert not board_url.endswith("index/")
        self.categories = None
        self.fora = None
        self.topics = []
        self.posts = []
        
        self.session = requests.Session()
        self.recorder = betamax.Betamax(
            self.session, cassette_library_dir=CASSETTE_LIBRARY_DIR
        )
    
    def get(self, url):
        logging.info("GET {}".format(url))
        r = self.session.get(url)
        soup = BS(r.text, 'html.parser')
        return soup
        
    def post(self, url, *args, **kwargs):
        logging.info("POST {}".format(url))
        r = self.session.post(url, *args, **kwargs)
        soup = BS(r.text, 'html.parser')
        return soup
    
    def login(self, username, password):
        data = {'tm': "05/03/2017,+18:38:18",
            'uname': username, 'pw': password,
            'cookie_on': '1', 'anon_on': '0'}
        login_page = self.post(self.board_url+'login/log_in/', data=data)
        if login_page.find(id='top_info').find('strong').get_text() != username:
            raise FailedToLogInError()
    
    def scrape_front(self):
        soup = self.get(self.board_url)
        
        a = soup.find('div', id='wrap').a
        self.board_name = a.text.strip()
        logging.info("Board name: {}".format(self.board_name))
        assert a['href'] == self.board_url+"index/"

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
                sibling_tds = tr_forum.next_sibling.next_sibling.find_all('td')
                td_topics, td_replies = sibling_tds[-2:] # Trash is missing viewers
                
                if tr_forum['id'] == "trash":
                    forum_id = -1
                else:
                    forum_id = tr_forum['id'].split('-')[1]
            
                forum = Forum(
                    id          = forum_id,
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
        soup = self.get("{}{}/?x={}".format(forum.url, page, 90))
        
        last_page = get_last_page(soup)        
        topics = []
        
        for tr in soup.find('table', class_='posts').find_all('tr'):
            if 'class' not in tr.attrs: continue
            # the page list is only in the way
            ul_pages = tr.find(class_='c_cat-title').find('ul', class_='cat-topicpages')
            if ul_pages:
                ul_pages.decompose()
            topic = Topic(
                id          = tr.find(class_='c_cat-title').a['href'].split('/')[-2],
                url         = tr.find(class_='c_cat-title').a['href'],
                forum_id    = forum.id,
                title       = tr.find(class_='c_cat-title').a.text.strip(),
                description = tr.find(class_='description').text.strip(),
                tags        = None,
                pinned      = tr.find(class_='c_cat-title').text.startswith("Pinned:"),
                start_date  = tr.find(class_='c_cat-title').a['title'],
                starter_id  = tr.find(class_='c_cat-starter').a['href'].split('/')[-2],
                num_replies = tr.find(class_='c_cat-replies').text.replace(',', ''),
                num_views   = tr.find(class_='c_cat-views').text.split()[0].replace(',', '')
            )
            
            topic.start_date = datetime.strptime(topic.start_date.split("Start Date ")[1], DATETIME_FORMAT)
            
            topics.append(topic)
        
        return topics, last_page
    
    def scrape_forum(self, forum):
        forum_topics, last_page = self.scrape_forum_page(forum, 1)
        
        for page in range(2, last_page+1):
            forum_topics += self.scrape_forum_page(forum, page)[0]
            
        logging.info("Scraped {} topics from forum {}".format(len(forum_topics), forum))
        self.topics += forum_topics

    def scrape_topic_page(self, topic, page):
        soup = self.get("{}{}/?x={}".format(topic.url, page, 90))
        
        last_page = get_last_page(soup)
        posts = []
        
        table = soup.find('table', id='topic_viewer')
        
        topic_trs = table.find_all('tr')[2:-2]
        for post_trs in [topic_trs[i:i+5] for i in range(0, len(topic_trs), 5)]:
            trs = post_trs
            postinfo = trs[0].find('td', class_='c_postinfo')
            post = Post(
                id          = trs[0]['id'].split('-')[1],
                url         = postinfo.a['href'],
                edit_url    = trs[3].find('td', class_='c_footicons').find(class_='left').a['href'],
                topic_id   = topic.id,
                user_id     = trs[0].find('a', class_='member')['href'].split('/')[-2],
                number      = postinfo.a.text.split("#")[-1],
                post_datetime = datetime.strptime(postinfo.find(class_='left').text.strip(), DATETIME_FORMAT),
                ip          = postinfo.find(class_='right').find(class_='desc').text.split('IP: ')[1].strip(),
                post_html   = trs[1].find('td', class_='c_post').encode_contents().strip()
            )
            posts.append(post)
        
        return posts, last_page
    
    def scrape_topic(self, topic):
        topic_posts, last_page = self.scrape_topic_page(topic, 1)
        
        for page in range(2, last_page+1):
            topic_posts += self.scrape_topic_page(topic, page)[0]
        
        logging.info("Scraped {} posts from topic {}".format(len(topic_posts), topic))
        self.posts += topic_posts
    
    
    def scrape_all(self):
        self.scrape_front()
        for forum in self.fora:
            self.scrape_forum(forum)
        
        for topic in self.topics:
            self.scrape_topic(topic)

zs = ZetaboardsScraper(board_url)
zs.login(config.USERNAME, config.PASSWORD)

if CASSETTE_NAME:
    with zs.recorder.use_cassette(CASSETTE_NAME):
        zs.scrape_all()
else:
    zs.scrape_all()

print("20/{} topics:".format(len(zs.topics)))

for topic in zs.topics[0:30]:
    print("* {}".format(topic))

print("20/{} posts:".format(len(zs.posts)))

for p in zs.posts[0:30]:
    print("* {}".format(p))

