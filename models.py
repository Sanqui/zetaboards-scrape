import attrs

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
