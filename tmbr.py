import praw
from pprint import pprint
from prawoauth2 import PrawOAuth2Mini
import time

from peewee import *
from peewee import OperationalError
from peewee import DoesNotExist

from tokens import app_key, app_secret, access_token, refresh_token
from settings import scopes, user_agent, bot_name, bot_password

reddit_client = praw.Reddit(user_agent=user_agent)
oauth_helper = PrawOAuth2Mini(reddit_client,app_key=app_key,app_secret=app_secret,access_token=access_token,scopes=scopes,refresh_token=refresh_token)
reddit_client.login(bot_name,bot_password,disable_warning=True)
db = SqliteDatabase('db/tmbr.db')
counting_submissions = []
last_checked_comment = []
active_submissions = []
used_star_symbols = [u'\u2605',u'\u2606',u'\u235F',u'\u2364',u'\u2726',u'\u2727',u'\u2728',u'\u269D',u'\u2729',u'\u272A',u'\u272B',u'\u272C',u'\u272D',u'\u272E',u'\u272F',
u'\u2730',u'\u2B50',u'\u2B51',u'\u2B52',u'\u1F31F',u'\u1F320',u'\u2721',u'\u2736',u'\uA673',u'\u1F52F',u'\u2055',u'\u2734',u'\u2735',u'\u2737',
u'\u2738',u'\u2742',u'\u2739']

response_head = ""
response_tail = "\n\n-------------------------------------------------\n\n^^I ^^am ^^a ^^bot. ^^You ^^can ^^complain ^^to ^^my ^^master ^^/u/Terdol ^^or ^^mods ^^at ^^/r/TMBR"
        
class CountingSubmission(Model):
    submission_id = CharField()
    bot_comment_id = CharField()
    author = CharField()
    subreddit = CharField()
    
    class Meta:
        database = db
    
def initialize_db():
    global db
    db.connect()
    try:
        db.create_tables([CountingSubmission,])
    except OperationalError:
        pass

def deinit():
    global db
    db.close()

def log_this_comment(comment, TableName=CountingSubmission):
    global counting_submissions
    comment_data = TableName(bot_comment_id=comment.id,
                             author=comment.author.name,
                             submission_id=comment.parent_id[3:], subreddit=comment.subreddit.display_name)
    comment_data.save()
    counting_submissions.append(comment.parent_id[3:])
    
def already_has_bot_comment(submission_id, only_db=False):
    global counting_submissions
    global reddit_client
    if submission_id in counting_submissions:
        return True
    try:
        CountingSubmission.select().where(
            CountingSubmission.submission_id == submission_id).get()
        return True
    except DoesNotExist:
        if only_db:
            return False
    sub = reddit_client.get_submission(submission_id=submission_id)
    sub.replace_more_comments(limit=None,treshold=1)
    comm = praw.helper.flatten_tree(sub.comments)
    for c in comm:
        if c.author.name == bot_name:
            log_this_comment(c)
            break
        
        
def counter_table(a,b,c):
    result = ''
    result += 'COUNTER   |          |\n'
    result += '----------|----------|\n'
    result += 'agree     |'
    result += ' '*(10-len(str(a)))+str(a)+'|\n'
    result += 'disagree  |'
    result += ' '*(10-len(str(b)))+str(b)+'|\n'
    result += 'undecided |'
    result += ' '*(10-len(str(b)))+str(c)+'|\n'
    return result

def make_new_comment(_submission_id,a=0,b=0,c=0,TableName=CountingSubmission):
    global reddit_client
    sub = reddit_client.get_submission(submission_id=_submission_id)
    response = response_head + counter_table(a,b,c) + response_tail
    comment = sub.add_comment(response)
    #sticky - requires login on mod
    #comment.distinguish(sticky=True)
    log_this_comment(comment)

def edit_comment(comment,a=0,b=0,c=0):
    response = response_head + counter_table(a,b,c) + response_tail
    comment.edit(response)
    
def check_condition(c):
    if "meme" in c.body.lower():
        for rep in c.replies:
            if rep.author.name==bot_name:
                return False
        return True
    return False
    
def clear_subreddit(sub):
    for c in reddit_client.get_comments(sub):
        if c.author.name==bot_name:
            c.delete()
    q = CountingSubmission.delete().where(str(CountingSubmission.subreddit).lower() == sub.lower())
    q.execute()
    
def remove_downvoted():
    global reddit_client
    bot_redditor = reddit_client.get_redditor(bot_name)
    for c in bot_redditor.get_comments(limit=None):
        if c.score<0:
            c.delete()

def recalculate_active_submissions():
    global reddit_client
    global active_submissions
    a=0
    b=0
    c=0
    for id in active_submissions:
        sub = reddit_client.get_submission(submission_id=id)
        sub.replace_more_comments(limit=None,treshold=1)
        bot_comment = None
        flat_comments = praw.helper.flatten_tree(sub.comments)
        for com in flat_comments:
            if c.author.name == bot_name:
                bot_comment = com
                continue
            if '!agree' in c.body.lower():
                a += 1
            if '!disagree' in c.body.lower():
                b += 1
            if '!undecided' in c.body.lower():
                c += 1
        edit_comment(bot_comment,a,b,c)
    active_submissions = []
            
def scan_comments_for_activity():
    global reddit_client
    for c in reddit_client.get_comments('TMBR'):
        if '!agree' not in c.body.lower() and '!disagree' not in c.body.lower() and '!undecided' not in c.body.lower():
            continue
        if c.author.name == bot_name:
            continue
        if not already_has_bot_comment(c.link_id[3:]):
            make_new_comment(c.link_id[3:])
        active_submissions.append(c.link_id[3:])

def strip_stars(flair):
    user = flair['user']
    flair_text = flair['flair_text']
    #if u'\u2606' in flair_text or u'\2605' in flair_text:
    
#def repopulate_database():
    
    
    
def main_loop():
    while True:
        scan_comments_for_activity()
        recalculate_active_submissions()
        #remove_downvoted()
        time.sleep(600)
    
        
if __name__ == '__main__':
    oauth_helper.refresh(force=True)
    initialize_db()
    main_loop()
    deinit()