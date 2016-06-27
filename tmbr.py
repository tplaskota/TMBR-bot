import praw
import pprint
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
response_tail = "\n\n-------------------------------------------------\n\n^^I ^^am ^^a ^^bot. ^^You ^^can ^^complain ^^to ^^my ^^master ^^/u/Terdol ^^or ^^provide ^^feedback ^^at ^^/r/TerdolBot"

class RepliedComments(Model):
    comment_id = CharField()
    author = CharField()
    subreddit = CharField()

    class Meta:
        database = db
        
class CountingSubmission(Model):
    submission_id = CharField()
    bot_comment_id = CharField()
    
    class Meta:
        database = db
    
def initialize_db():
    db.connect()
    try:
        db.create_tables([RepliedComments,CountingSubmission])
    except OperationalError:
        pass

def deinit():
    db.close()

def is_already_replied(comment_id):
    if comment_id in replied_comments:
        return True
    try:
        RepliedComments.select().where(
            RepliedComments.comment_id == comment_id).get()
        return True
    except DoesNotExist:
        return False

def log_this_comment(comment, TableName=RepliedComments):
    comment_data = TableName(comment_id=comment.id,
                             author=comment.author.name,
                             subreddit=comment.subreddit.display_name)
    comment_data.save()
    replied_comments.append(comment.id)
    
def already_has_bot_comment(submission_id):
    if submission_id in counting_submissions:
        return True
    try:
        CountingSubmission.select().where(
            CountingSubmission.submission_id == submission_id).get()
        return True
    except DoesNotExist:
        return False
		
def counter_table(a,b):
	result = ''
	result += 'COUNTER   |          |\n'
	result += '----------|----------|\n'
	result += 'agree     |'
	result += ' '*(10-len(str(a)))+str(a)+'|\n'
	result += 'disagree  |'
	result += ' '*(10-len(str(b)))+str(b)+'|\n'

def make_new_comment(_submission_id,TableName=CountingSubmission):
    submission_data = TableName(submission_id=_submission_id,
                                bot_comment_id = '0')
    submission_data.save()
    counting_submissions.append(_submission_id)
    submission = reddit_client.get_submission(submission_id=_submission_id)
    #pprint.pprint(vars(submission))
    #pprint.pprint(dir(submission))
	submission.add_comment()

def check_condition(c):
    if "meme" in c.body.lower():
        for rep in c.replies:
            if rep.author.name==bot_name:
                return False
        return True
    return False

def bot_action(c):
    print(c.body)

def post_to_terdolbot(c):
    c.reply(response_head + c.body + response_tail)
    
def clear_subreddit(sub):
    for c in reddit_client.get_comments(sub):
        if c.author.name==bot_name:
            c.delete()
    q = RepliedComments.delete().where(str(RepliedComments.subreddit).lower() == sub.lower())
    q.execute()
    
def remove_downvoted():
    for c in bot_name.get_comments(limit=None):
        if c.score<0:
            c.delete()
			
def comment_is_assigned(c):
	try:
		s = CountingSubmission.select().where(
            CountingSubmission.submission_id == c.link_id[3:]).get()
		return s.bot_comment_id != '0'
    except DoesNotExist:
        return False
		

def try_to_assign_comment(c):
	
    
def deal_with_submissions():
    pass

def main_loop():
    #for c in praw.helpers.comment_stream(reddit_client, 'dota2'):
    #    if check_condition(c):
    #        bot_action(c)
    #        for c in dir(c):
    #            print(c)
    #        break
    #  
    #for c in praw.helpers.comment_stream(reddit_client, 'terdolbot'):
    #    if check_condition(c):
    #        post_to_terdolbot(c)
    #for c in praw.helpers.comment_stream(reddit_client, 'TMBR'):
    #    if 'meme' not in c.body.lower():
    #        continue
    #    if c.author.name == bot_name:
    #        continue
    #    if is_already_replied(c.id):
    #        continue
    #    response = response_head + c.body + response_tail
    #    log_this_comment(c)
    #    c.reply(response)
    for c in reddit_client.get_comments('TMBR'):
        if 'agree' not in c.body.lower() and 'disagree' not in c.body.lower():
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
    #clear_subreddit('terdolbot')
    i = 0
    #while True:
        
    main_loop()
    deinit()
    #clear_terdolbot()