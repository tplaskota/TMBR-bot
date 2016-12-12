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
moderator_list = [mod.name for mod in reddit_client.get_subreddit('tmbr').get_moderators()]
tmbr_subreddit = reddit_client.get_subreddit('tmbr')
counting_submissions = []
last_checked_comment = []
active_submissions = []
used_star_symbols = [u'\u2605',u'\u2606',u'\u235F',u'\u2364',u'\u2726',u'\u2727',u'\u2728',u'\u269D',u'\u2729',u'\u272A',u'\u272B',u'\u272C',u'\u272D',u'\u272E',u'\u272F',
u'\u2730',u'\u2B50',u'\u2B51',u'\u2B52',u'\u1F31F',u'\u1F320',u'\u2721',u'\u2736',u'\uA673',u'\u1F52F',u'\u2055',u'\u2734',u'\u2735',u'\u2737',
u'\u2738',u'\u2742',u'\u2739']

response_head = ""
response_tail = "\n\n-------------------------------------------------\n\n^^I ^^am ^^a ^^bot. ^^You ^^can ^^complain ^^to ^^my ^^master ^^/u/Terdol ^^or ^^mods ^^at ^^/r/TMBR"
bot_commands = ["!agreewithop","!disagreewithop","!undecided"]
        
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
    sub.replace_more_comments(limit=None,threshold=0)
    comm = praw.helpers.flatten_tree(sub.comments)
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
    result += ' '*(10-len(str(c)))+str(c)+'|\n'
    return result
    
def debate_rules(tag='Debate'):
    result = '\n\n'
    result += 'Hello, this thread is tagged as "'+tag+'"\n\n'
    result += 'Quick reminder of posting rules in debate threads:\n\n'
    result += '* Redditors with flair might comment freely, but are unable to add their votes to automatic poll.\n'
    result += '* Redditors without flair can only add their votes to automatic poll via usuall commands, but can not comment anything else.\n\n'
    result += 'In case of breaking these restrictions comments will be removed without warning. For more information visit (here)['+debate_rules_link+'].\n'
    return result

def make_new_comment(_submission_id,a=0,b=0,c=0,TableName=CountingSubmission):
    global reddit_client
    sub = reddit_client.get_submission(submission_id=_submission_id)
    print(_submission_id)
    try:
        response = response_head + counter_table(a,b,c)
        if sub.link_flair_text != None and 'debate' in sub.link_flair_text.lower():
            response += debate_rules(sub.link_flair_text)
        response += response_tail
        comment = sub.add_comment(response)
        #sticky - requires login on mod
        comment.distinguish(sticky=True)
        log_this_comment(comment)
    except praw.errors.APIException as e:
        return False
    return True

def edit_comment(comment,b_debate=False,a=0,b=0,c=0):
    response = response_head + counter_table(a,b,c)
    if b_debate:
        response += debate_rules(sub.link_flair_text)
    response += response_tail
    comment.edit(response)
    
def clear_subreddit(sub):
    for c in reddit_client.get_comments(sub,limit=None):
        if c.author == None: #deleted
            continue
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
    for id in active_submissions:
        votes=[[],[],[],]
        banned_on_this_submission = []
        bot_comment = None
        one_bot_comment_flag = False
        b_debate_submission = False
        while not one_bot_comment_flag:
            sub = reddit_client.get_submission(submission_id=id)
            b_debate_submission = sub.link_flair_text != None and 'debate' in sub.link_flair_text.lower()
            sub.replace_more_comments(limit=None,threshold=0)
            flat_comments = praw.helpers.flatten_tree(sub.comments)
            bot_comment = [com for com in flat_comments if com.author != None and com.author.name.lower() == bot_name.lower()]
            if bot_comment == None:
                raise Exception("LOLWUT")
            elif len(bot_comment) > 1:
                for com in bot_comment:
                    if not com.stickied:
                        com.delete()
            elif len(bot_comment) == 1:
                one_bot_comment_flag = True
            elif len(bot_comment) == 0:
                make_new_comment(id)
        
            
        for com in flat_comments:
            if com.author == None: #comment deleted
                continue
            if com.author.name == bot_name:
                if bot_comment == None:
                    bot_comment = com
                    continue
                else:
                    #com.delete()
                    continue
            if com.author.name in banned_on_this_submission:
                continue
            command_index = None
            for i,command in enumerate(bot_commands):
                if command in com.body.lower():
                    if command_index != None:
                        command_index = None
                        break
                    else:
                        command_index = i
            if command_index != None:
                author = com.author.name
                ap = True
                for i,command in enumerate(bot_commands):
                    if author in votes[i] and i==command_index:
                        ap = False
                    if author in votes[i] and i!=command_index:
                        ap = False
                        votes[i].remove(author)
                        banned_on_this_submission.append(author)
                        break
                if ap:
                    votes[command_index].append(author)
                        
                    
        if sum([len(a) for a in votes])>0:
            if bot_comment==None:
                make_new_comment(com.link_id[3:],*[len(a) for a in votes])
                for com in flat_comments:
                    if com.author == None: #comment deleted
                        continue
                    if com.author.name == bot_name:
                        bot_comment = com
                        break
                if bot_comment == None:
                    has_comment = False
                else:
                    has_comment = True
            else:
                has_comment = True
            if has_comment:
                time.sleep(3)
                if type(bot_comment) is list:
                    bot_comment=bot_comment[0]
                edit_comment(bot_comment, b_debate_submission, *[len(a) for a in votes])
    active_submissions = []
                
def scan_comments_for_activity():
    global reddit_client
    global active_submissions
    for c in reddit_client.get_comments('TMBR'):
        if 1 != len([1 for command in bot_commands if command in c.body.lower()]): #check agree/disagre/undecided, only one of those can be present
            continue
        if c.author == None: #comment deleted
            continue
        if c.author.name == bot_name:
            continue
        active_submissions.append(c.link_id[3:])
    active_submissions = list(set(active_submissions))

def strip_stars(flair):
    user = flair['user']
    flair_text = flair['flair_text']
    #if u'\u2606' in flair_text or u'\2605' in flair_text:
    
def flag_all_submissions_for_activity():
    global reddit_client
    global active_submissions
    t = 137393280 #july 2013
    active_submissions = [a.id for a in reddit_client.get_subreddit('tmbr').search('timestamp:{0}..{1}'.format(int(t),int(time.time())),syntax='cloudsearch',limit=None,sort='new')]

    
def moderate_debates():
    global reddit_client
    global active_submissions
    debate_submissions = [a for a in reddit_client.get_subreddit('tmbr').get_new(limit=1000) if a.link_flair_text != None and 'debate' in a.link_flair_text.lower()]
    debate_submissions.sort(key=lambda x:x.created_utc, reverse=True)
    for subm in debate_submissions:
        active_submissions.append(subm.id)
    for d_sub in debate_submissions:
        print("Debate submission moderation subscribed:",d_sub.title)
        d_sub.replace_more_comments(limit=None,threshold=0)
        flat_comments = praw.helpers.flatten_tree(d_sub.comments)
        for com in flat_comments:
            if com.author == None: #deleted
                continue
            if com.author.name in moderator_list: #moderators including bot itself
                continue
            if tmbr_subreddit.get_flair(com.author)['flair_text'] != None:
                #flaired user
                if 0 < len([1 for command in bot_commands if command in com.body.lower()]):
                    com.remove()
            else:
                #not-flaired user
                if 1 != len([1 for command in bot_commands if command == com.body.lower()]):
                    com.remove()
        
        
    
def main_loop():
    while True:
        moderate_debates()
        scan_comments_for_activity()
        #flag_all_submissions_for_activity()
        recalculate_active_submissions()
        #remove_downvoted()
        time.sleep(30)
        #break
    
        
if __name__ == '__main__':
    oauth_helper.refresh(force=True)
    initialize_db()
    main_loop()
    deinit()
