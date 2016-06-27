import praw
from pprint import pprint
from prawoauth2 import PrawOAuth2Mini

from peewee import *
from peewee import OperationalError
from peewee import DoesNotExist

from tokens import app_key, app_secret, access_token, refresh_token
from settings import scopes, user_agent, bot_name

reddit_client = praw.Reddit(user_agent=user_agent)
oauth_helper = PrawOAuth2Mini(reddit_client,app_key=app_key,app_secret=app_secret,access_token=access_token,scopes=scopes,refresh_token=refresh_token)
db = SqliteDatabase('db/tmbr.db')
replied_comments = []
bot_comments_with_counter = []
counting_submissions = []
last_checked_comment = []

response_head = "Hi!\n\n"
response_tail = "\n\n-------------------------------------------------\n\n^^I ^^am ^^a ^^bot. ^^You ^^can ^^complain ^^to ^^my ^^master ^^/u/Terdol ^^or ^^mods ^^at ^^/r/TMBR"
        
class CountingSubmission(Model):
    submission_id = CharField()
    bot_comment_id = CharField()
    author = CharField()
    subreddit = CharField()
    
    class Meta:
        database = db
    
def initialize_db():
    db.connect()
    try:
        db.create_tables([CountingSubmission,])
    except OperationalError:
        pass

def deinit():
    db.close()

def log_this_comment(comment, TableName=CountingSubmission):
    comment_data = TableName(bot_comment_id=comment.id,
                             author=comment.author.name,
                             submission_id=comment.parent_id[3:], subreddit=comment.subreddit.display_name)
    comment_data.save()
    counting_submissions.append(comment.parent_id[3:])
    
def already_has_bot_comment(submission_id):
    if submission_id in counting_submissions:
        return True
    try:
        CountingSubmission.select().where(
            CountingSubmission.submission_id == submission_id).get()
        return True
    except DoesNotExist:
        return False
        
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
    sub = reddit_client.get_submission(submission_id=_submission_id)
    response = response_head + counter_table(a,b,c) + response_tail
    comment = sub.add_comment(response)
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
    for c in bot_name.get_comments(limit=None):
        if c.score<0:
            c.delete()


def main_loop():
    #for c in praw.helpers.comment_stream(reddit_client, 'TMBR'):
    #    if 'text' not in c.body.lower():
    #        continue
    #    if c.author.name == bot_name:
    #        continue
    #    if is_already_replied(c.id):
    #        continue
    #    response = response_head + c.body + response_tail
    #    log_this_comment(c)
    #    c.reply(response)

    for c in reddit_client.get_comments('TMBR'):
        if '!agree' not in c.body.lower() and '!disagree' not in c.body.lower() and '!undecided' not in c.body.lower():
            continue
        if c.author.name == bot_name:
            if not comment_is_assigned(c):
                try_to_assign_comment(c)
            continue
        if is_already_replied(c.id):
            continue
        if not already_has_bot_comment(c.link_id[3:]):
            make_new_comment(c.link_id[3:])
        #update_submission_counter(c.link_id[3:])
        print('\n')
        #pprint.pprint(vars(c))
        
if __name__ == '__main__':
    oauth_helper.refresh(force=True)
    initialize_db()
    i = 0
    #while True:
        
    main_loop()
    deinit()