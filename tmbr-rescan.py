from tmbr import *

def reinitialize():
    flag_all_submissions_for_activity()
    recalculate_active_submissions()
    
if __name__=='__main__':
    oauth_helper.refresh(force=True)
    initialize_db()
    reinitialize()
    deinit()