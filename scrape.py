import yaml
import requests
from bs4 import BeautifulSoup as BS
import betamax
from attr import attrs, attrib
import logging
import sys
import time
from datetime import datetime
from pprint import pprint
import parsedatetime
cal = parsedatetime.Calendar()

from pdb import set_trace as bp

import config

board_url = config.BOARD_URL

CASSETTE_LIBRARY_DIR = 'cassettes/'
CASSETTE_NAME = sys.argv[1] if len(sys.argv) > 1 else None
CASSETTE_NAME = CASSETTE_NAME.split(CASSETTE_LIBRARY_DIR)[-1]

TEST_MAX = 5

DATETIME_FORMAT = "%b %d %Y, %I:%M %p"
def zetadate(string):
    try:
        return datetime.strptime(string, DATETIME_FORMAT)
    except ValueError:
        # ZetaBoards sometimes uses dates like "15 minutes ago",
        # so here's hoping parsedatetime will handle them all
        time_struct, parse_status = cal.parse(string)
        return time_struct

logging.basicConfig(level=logging.INFO,
    format='%(asctime)-15s %(levelname)-8s %(message)s')

class FailedToLogInError(Exception): pass

@attrs
class Member():
    id = attrib(convert=int)
    name = attrib()
    register_ip = attrib()
    last_active = attrib()
    email = attrib()
    post_count = attrib(convert=int)
    warning_level = attrib(convert=int)
    group_id = attrib(convert=int)
    title = attrib()
    location = attrib()
    aim = attrib()
    yim = attrib()
    msn = attrib()
    homepage = attrib()
    interests = attrib()
    signature = attrib()
    photo_url = attrib()
    avatar_url = attrib()
    custom_fields = attrib()
    
    def __str__(self):
        return "Member({}, {})".format(self.id, self.name)

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
    mark = attrib()
    pinned = attrib()
    start_date = attrib()
    starter_id = attrib(convert=int)
    num_replies = attrib(convert=int)
    num_views = attrib(convert=int)
    
    def __str__(self):
        return "Topic({}, {})".format(self.id, self.title)

@attrs
class MovedTopic():
    topic_id = attrib(convert=int)
    from_forum_id = attrib(convert=int)
    
    def __str__(self):
        return "MovedTopic({})".format(self.id)

@attrs
class Post():
    id = attrib(convert=int)
    url = attrib()
    edit_url = attrib()
    topic_id = attrib()
    member_id = attrib()
    number = attrib()
    post_datetime = attrib()
    ip = attrib()
    post_html = attrib()
    
    def __str__(self):
        return "Post({}, {}...)".format(self.id, self.post_html[0:20])

@attrs
class PostSource():
    id = attrib(convert=int)
    post_source = attrib()
    include_signature = attrib()
    display_emoticons = attrib()

@attrs
class PostRevision():
     post_id = attrib(convert=int)
     member_id = attrib(convert=int)
     ip = attrib()
     datetime = attrib()
     post_html = attrib()

@attrs
class Shout():
    id = attrib(convert=int)
    member_id = attrib(convert=int)
    datetime = attrib()
    text = attrib()

@attrs
class Poll():
    id = attrib(convert=int)
    question = attrib()
    num_choices = attrib()
    exclusive = attrib()
    answers = attrib()

@attrs
class CustomProfileField():
    id = attrib(convert=int)
    title = attrib()
    on_registration = attrib()
    admin_only = attrib()
    show_in_topics = attrib()
    type = attrib()
    multiple_choices = attrib()
    choices = attrib()

def get_last_page(soup):
    ul_pages = soup.find('ul', class_='cat-pages')
    if ul_pages:
        last_page = int(soup.find_all('li')[-1].text.strip())
    else:
        last_page = 1
    
    return last_page

class ZetaboardsScraper():
    def __init__(self, board_url, board_admin_url):
        self.board_url = board_url
        self.board_admin_url = board_admin_url
        assert not board_url.endswith("index/")
        self.categories = None
        self.fora = None
        self.topics = []
        self.posts = []
        self.post_sources = []
        self.post_revisions = []
        self.member_ids = []
        self.members = []
        self.shouts = []
        self.polls = []
        self.custom_profile_fields = []
        
        self.session = requests.Session()
        
        self.recorder = betamax.Betamax(
            self.session, cassette_library_dir=CASSETTE_LIBRARY_DIR
        )
    
    def get(self, url, *args, **kwargs):
        r = requests.Request("GET", url, *args, **kwargs)
        r = self.session.prepare_request(r)
        logging.info("GET {}".format(r.url))
        r = self.session.send(r)
        soup = BS(r.text, 'html.parser')
        return soup
        
    def post(self, url, *args, **kwargs):
        r = requests.Request("POST", url, *args, **kwargs)
        r = self.session.prepare_request(r)
        logging.info("POST {}".format(r.url))
        r = self.session.send(r)
        soup = BS(r.text, 'html.parser')
        return soup
    
    def login(self, username, password):
        data = {'tm': "05/03/2017,+18:38:18",
            'uname': username, 'pw': password,
            'cookie_on': '1', 'anon_on': '0'}
        login_page = self.post(self.board_url+'login/log_in/', data=data)
        if login_page.find(id='top_info').find('strong').get_text() != username:
            raise FailedToLogInError()
        
        data = {'name': username, 'pass': password}
        login_page_admin = self.post(self.board_admin_url+'?menu=login', data=data)
        
        submenu = login_page_admin.find(id='submenu')
        if not submenu or submenu.find('strong').get_text() != username:
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
            
            mark = tr.find_all(class_='c_cat-mark')[-1].img['alt']
            topic_id = int(tr.find(class_='c_cat-title').a['href'].split('/')[-2])
            
            if mark != "Moved":            
                topic = Topic(
                    id          = topic_id,
                    url         = tr.find(class_='c_cat-title').a['href'],
                    forum_id    = forum.id,
                    title       = tr.find(class_='c_cat-title').a.text.strip(),
                    description = tr.find(class_='description').text.strip() if tr.find(class_='description') else None,
                    tags        = None,
                    mark        = mark,
                    pinned      = tr.find(class_='c_cat-title').text.startswith("Pinned:"),
                    start_date  = zetadate(tr.find(class_='c_cat-title').a['title'].split("Start Date ")[1]),
                    starter_id  = tr.find(class_='c_cat-starter').a['href'].split('/')[-2],
                    num_replies = tr.find(class_='c_cat-replies').text.replace(',', ''),
                    num_views   = tr.find(class_='c_cat-views').text.split()[0].replace(',', '')
                )
                
                topics.append(topic)
            else:
                moved_topic = MovedTopic(
                    topic_id = topic_id,
                    from_forum_id = forum.id
                )
                
                topics.append(moved_topic)
        
        return topics, last_page
    
    def scrape_forum(self, forum):
        forum_topics, last_page = self.scrape_forum_page(forum, 1)
        
        for page in range(2, last_page+1):
            forum_topics += self.scrape_forum_page(forum, page)[0]
            
        logging.info("Scraped {} topics from forum {}".format(len(forum_topics), forum))
        self.topics += forum_topics
    
    def scrape_poll(self, topic, form_poll):
        poll_id = form_poll['id'].split('poll')[1]
        
        num_choices = form_poll.find('span', style="float: left;").strong
        if num_choices:
            num_choices = int(num_choices.text.split(' choices')[0])
        else:
            num_choices = 1
        
        soup = self.get(topic.url+"1/", params={'results': poll_id})
        
        form_poll = soup.find('form', id="poll{}".format(poll_id))
        
        answers = []
        
        for tr in form_poll.find_all('tr')[2:-1]:
            answer = str(tr.find('td', class_='c_poll-answer').contents[0]).strip()
            votes = int(tr.find('td', class_='c_poll-votes').strong.text)
            answers.append((answer, votes))
        
        poll = Poll(
            id = poll_id,
            question = form_poll.find('thead').text.strip(),
            num_choices = num_choices,
            exclusive = None, # TODO, this might require scraipng the edit page
            answers = answers
        )
        
        self.polls.append(poll)
        
    
    def scrape_topic_page(self, topic, page):
        soup = self.get("{}{}/?x={}".format(topic.url, page, 90))
        
        last_page = get_last_page(soup)
        posts = []
        
        table = soup.find('table', id='topic_viewer')
        
        if page == 1:
            for table_poll in soup.find_all('table', class_='poll'):
                self.scrape_poll(topic, table_poll.parent)
        
        topic_trs = table.find_all('tr')[2:-2]
        for post_trs in [topic_trs[i:i+5] for i in range(0, len(topic_trs), 5)]:
            trs = post_trs
            postinfo = trs[0].find('td', class_='c_postinfo')
            post = Post(
                id          = trs[0]['id'].split('-')[1],
                url         = postinfo.a['href'],
                edit_url    = trs[3].find('td', class_='c_footicons').find(class_='left').a['href'],
                topic_id    = topic.id,
                member_id   = trs[0].find('a', class_='member')['href'].split('/')[-2],
                number      = postinfo.a.text.split("#")[-1],
                post_datetime = zetadate(postinfo.find(class_='left').text.strip()),
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
    
    def scrape_post_source(self, post):
        soup = self.get(post.edit_url)
        
        post_source = PostSource(
            id = post.id,
            post_source = soup.find('textarea', id='c_post-text').text.strip(),
            include_signature = bool(soup.find('input', {'name':'sig'}).get('checked')),
            display_emoticons = bool(soup.find('input', {'name':'emo'}).get('checked'))
        )
        
        self.post_sources.append(post_source)
    
    def scrape_post_history(self, post):
        post_soup = BS(post.post_html, 'html.parser')
        editby = post_soup.find('div', class_='editby')
        if not editby: return
        editby.strong.decompose()
        if not editby.a: return
        edit_history_url = editby.a['href']
        
        soup = self.get(edit_history_url)
        table = soup.find('table', id='mod_screen')
        for tr in table.find_all('tr')[1:]:
            tds = tr.find_all('td')
            
            # blah blah bs workaround
            for br in tds[0].find_all("br"):
                br.replace_with('\n')

            lines = tds[0].text.strip().split('\n')
            
            post_revision = PostRevision(
                post_id = post.id,
                member_id = tds[0].a['href'].split('/')[-2],
                ip = lines[1].split(":")[1].strip(),
                datetime = zetadate(lines[2].split(":")[1].strip()),
                post_html = tds[1].encode_contents().strip()
            )
        
            self.post_revisions.append(post_revision)
    
    def scrape_member_list_page(self, page):
        params = {'sort': 'join_unix', 'order': 'a'}
        soup = self.get(self.board_url+"members/{}".format(page), params=params)
        
        last_page = get_last_page(soup)
        
        member_ids = []
        
        for tr in soup.find('table', id="member_list_full").find_all('tr', class_=['row1', 'row2']):
            tds = tr.find_all('td')
            
            member_ids.append(int(tds[0].a['href'].split('/')[-2]))
        
        return member_ids, last_page
        
    def scrape_member_list(self):
        member_ids, last_page = self.scrape_member_list_page(1)
        
        for page in range(2, last_page+1):
            member_ids += self.scrape_member_list_page(page)[0]
        
        logging.info("Scraped {} member ids".format(len(member_ids)))
        self.member_ids = member_ids
    
    def scrape_member_edit_page(self, member_id):
        params = {'menu': 'mem', 'c': '1', 'mid': member_id}
        soup = self.get(self.board_admin_url, params=params)
        
        form = soup.find('form')
        assert form.id != 'loginform'
        table = form.find('table')
        trs = table.find_all('tr')
        form = {e['name']: e.get('value', '') for e in table.find_all('input', {'name': True})}
        
        if 'av_url' in form:
            avatar_url = form['av_url']
        else:
            # This happens when a person is using one of the preselected
            # avatars
            avatar_url = table.find('img', class_='avatar')['src']
        
        member = Member(
            id          = member_id,
            name        = trs[0].text.strip().split("Editing Member: ")[1],
            register_ip = trs[2].find_all('td')[1].text,
            last_active = zetadate(trs[3].find_all('td')[1].text),
            email       = form['email'],
            post_count  = form['postcount'],
            warning_level = form['warned'],
            title       = form['mem_title'],
            group_id    = table.find(id='gid').find('option', selected=True)['value'],
            location    = form['loc'],
            aim         = form['aim'],
            yim         = form['yim'],
            msn         = form['msn'],
            homepage    = form['www'],
            interests   = table.find('textarea', {'name': 'interests'}).text.strip(),
            signature   = table.find('textarea', {'name': 'sig'}).text.strip(),
            photo_url   = form['photo'],
            avatar_url  = avatar_url,
            custom_fields = {}
        )
        
        for key, value in form.items():
            if key.startswith("choice_"):
                field_id = int(key.split("_")[1])
                member.custom_fields[field_id] = value
        
        for select in table.find_all('select'):
            if select['name'].startswith("choice_"):
                field_id = int(select['name'].split("_")[1])
                member.custom_fields[field_id] = select.find('option', selected=True)['value']
        
        self.members.append(member)
    
    def scrape_shoutbox_page(self, page):
        soup = self.get("{}stats/shout_archive/{}/".format(self.board_url, page))
        
        shouts = []
        last_page = get_last_page(soup)
        
        table_shoutbox = soup.find('table', id="sbx_archive")
        if not table_shoutbox:
            return [], -1
        
        for tr in table_shoutbox.find_all('tr'):
            if not tr.find_all('td'): continue
            delete_link = tr.find_all('td')[-1].find_all('a')[-1]
            assert delete_link.text.strip() == "(X)"
            shout_id = delete_link['onclick'].split('(')[1].rstrip(');')
            delete_link.decompose()
            
            shout = Shout(
                id = shout_id,
                member_id = tr.find('a', class_='member')['href'].split('/')[-2],
                datetime = zetadate(tr.find('td', class_='c_desc').find('small').text),
                text = tr.find_all('td')[-1].encode_contents().strip()
            )
            
            shouts.append(shout)
        
        return shouts, last_page
    
    def scrape_shoutbox(self):
        shouts, last_page = self.scrape_shoutbox_page(1)
        
        for page in range(2, last_page+1):
            shouts += self.scrape_shoutbox_page(page)[0]
        
        logging.info("Scraped {} shouts".format(len(shouts)))
        self.shouts = shouts
    
    def scrape_custom_profile_fields(self):
        soup = self.get(self.board_admin_url, params={'menu': 'mem', 'c': 32})
        
        for tr in soup.find_all('table')[0].find_all('tr')[2:]:
            tds = tr.find_all('td')
            title = tds[0].text.strip()
            type = tds[1].text.strip()
            edit_url = tds[3].a['href']
            id = edit_url.split('=')[-1]
            
            soup_edit = self.get(edit_url)
            def radio(name):
                input = soup_edit.find('input', {'name': name, 'value': 1})
                if not input:
                    return None
                return bool(input.get('checked', False))
            
            allow_multiple = None
            choices = []
            
            if type == "Multiple choice":
                for input in soup_edit.find_all('input'):
                    if input['name'].startswith('old_choice'):
                        choices.append(input['value'])
            
            
            field = CustomProfileField(
                id = id,
                title = title,
                type = type,
                on_registration = radio('reg_optional'),
                admin_only = radio('admin_edit_only'),
                show_in_topics = radio('topic_view'),
                multiple_choices = radio('maxlen'), # maxlen, seriously zetaboards?
                choices = choices
            )
            
            self.custom_profile_fields.append(field)
    
    def scrape_all(self):
        self.scrape_front()
        
        self.scrape_custom_profile_fields()
        
        self.scrape_member_list()
        
        for member_id in self.member_ids[0:TEST_MAX]:
            self.scrape_member_edit_page(member_id)
        
        self.scrape_shoutbox()
        
        for forum in self.fora[0:TEST_MAX]:
            self.scrape_forum(forum)
        
        for topic in self.topics[0:TEST_MAX]:
            self.scrape_topic(topic)
        
        for post in self.posts[0:TEST_MAX]:
            self.scrape_post_source(post)
            self.scrape_post_history(post)

zs = ZetaboardsScraper(board_url, config.BOARD_ADMIN_URL)

zs.login(config.USERNAME, config.PASSWORD)

if CASSETTE_NAME:
    with zs.recorder.use_cassette(CASSETTE_NAME.rstrip('+'),
        match_requests_on=['method', 'uri', 'body'],
        record='new_episodes' if CASSETTE_NAME.endswith('+') else 'once'):
        
        zs.scrape_all()
else:
    zs.scrape_all()


for items_name in "custom_profile_fields shouts members polls topics posts".split():
    items = getattr(zs, items_name)
    if items:
        print("Example {} from a total of {}:".format(items_name, len(items)))
        for i, item in enumerate(items[0:10]):
            print(" [{}] {}".format(i, item))
        print(" [{}] {}".format(len(items)-1, items[-1]))
    else:
        print("No {} scraped.".format(items_name))


#for p in zs.post_sources[0:30]:
#    print("* {}".format(p))

