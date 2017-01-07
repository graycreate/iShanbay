# encoding: utf-8

import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os
import time
from urlparse import urlparse
from workflow import Workflow3, web
from workflow import ICON_WEB, ICON_WARNING
from workflow import PasswordNotFound
from workflow.notify import notify

CLIENT_ID = 'de0af3ca452ddb078e6d'
TOKEN_KEY = 'me.ghui.shanbay_alfred_workflow_token'
TOKEN_EXPIRES_IN = 'expires_in'
SEARCH_URL = 'https://api.shanbay.com/api/v1/bdc/search/'
LEARNING_URL = 'https://api.shanbay.com/bdc/learning/'
AUTHORIZE_URL = 'https://api.shanbay.com/oauth2/authorize/'
EXAMPLE_URL = 'https://api.shanbay.com/bdc/example/'
NOTE_URL = 'https://api.shanbay.com/bdc/note/'
VOCABULARY_URL = 'https://www.shanbay.com/bdc/vocabulary/%d/'
SEPARATOR = ' '

ICON_EXAMPLE = 'example.png'
ICON_NOTE = 'note.png'


log = None


def get_env(key):
    return os.environ[key]


def is_authed():
    expire_date = wf.stored_data(TOKEN_EXPIRES_IN)
    log.debug("expire_date: " + str(expire_date))
    if (expire_date < time.time()):
        return False
    try:
        wf.get_password(TOKEN_KEY)
        return True
    except PasswordNotFound:
        return False


def save_token(url):
    # todo
    parse_result = urlparse(url)
    data = dict(map(lambda x: x.split('='), parse_result.fragment.split('&')))
    token = data['access_token']
    wf.save_password(TOKEN_KEY, token)
    expire = int(data['expires_in']) + time.time()
    wf.store_data(TOKEN_EXPIRES_IN, expire)
    notify('授权成功', '授权码已保存到Keychain')


def get_token():
    return wf.get_password(TOKEN_KEY)


def do_auth():
    url = '%s?client_id=%s&response_type=token' % (AUTHORIZE_URL, CLIENT_ID)
    os.system('open "%s"' % url)


def get_example(word_id):
    if word_id == 0:  # invalid
        return 0

    params = dict(vocabulary_id=word_id)
    r = web.get(EXAMPLE_URL, params)
    r.raise_for_status()
    examples = sorted(r.json()['data'], key=lambda value: value[
        'likes'], reverse=True)
    max_example_num = int(get_env('max_example_num'))
    examples = examples[:max_example_num]

    for example in examples:
        title = example['annotation'].replace(
            '<vocab>', '').replace('</vocab>', '')
        subtitle = example['translation']
        item = wf.add_item(title=title, subtitle=subtitle,
                           arg=word_id, valid=False, icon=ICON_EXAMPLE)
        item.add_modifier(key='ctrl', subtitle=title, arg=None, valid=False)


def get_note(word_id):
    if not is_authed():
        return 0
    params = dict(vocabulary_id=word_id, access_token=get_token())
    r = web.get(NOTE_URL, params)
    r.raise_for_status()
    notes = sorted(r.json()['data'], key=lambda value: value[
        'likes'], reverse=True)
    max_notes_num = int(get_env('max_note_num'))
    notes = notes[:max_notes_num]
    for note in notes:
        title = note['content']
        subtitle = note['user']['nickname']
        item = wf.add_item(title=title, subtitle='作者: ' +
                           subtitle, arg=word_id, valid=False, icon=ICON_NOTE)
        item.add_modifier(key='ctrl', subtitle=title, arg=None, valid=False)


def search(word):
    params = dict(word=word)
    r = web.get(SEARCH_URL, params)
    r.raise_for_status()
    result = r.json()
    word_id = 0  # invalid id
    if result['status_code'] == 0:  # success
        log.debug('setWord: ' + str(word))
        wf.store_data('current_word', word)
        data = result['data']
        word_id = str(data['id'])
        word_And_id = data['content'] + SEPARATOR + word_id
        pron = data['pron']
        title = "%s /%s/" % (word, pron)
        subtitle = data['definition']
        subtitle = subtitle.replace('\n', '|')  # .replace('&', '')
        item = wf.add_item(title=title, subtitle=subtitle,
                           arg=word_id, valid=True)
        item.add_modifier(key='ctrl', subtitle='发音', arg=word)
    get_example(word_id)
    get_note(word_id)
    wf.send_feedback()


def say(word):
    bashCommand = 'say ' + word
    os.system(bashCommand)


def add(word_id):
    log.debug('word_id: ' + str(word_id))
    if not is_authed():
        notify('请授权后再添加!', '详情: ghui.me/alfred/ishanbay')
        do_auth()
        return 0
    else:
        # do add
        params = dict(id=word_id, access_token=get_token())
        r = web.post(LEARNING_URL, None, params)
        r.raise_for_status()
        if r.json()['status_code'] == 0:
            word = wf.stored_data('current_word')
            notify('添加成功', word + ' 已添加到生词本')


def main(wf):
    options = int(wf.args[0].strip())
    query = wf.args[1].strip()
# CASE ...
    if options == 0:
        search(query)
    elif options == 1:
        say(query)
    elif options == 2:
        add(query)
    elif options == 3:
        save_token(query)
    else:
        search(query)

if __name__ == u"__main__":
    wf = Workflow3(update_settings={
        'github_slug': 'ghuiii/ishanbay'
    })
    log = wf.logger
    sys.exit(wf.run(main))
    if wf.update_available:
        wf.start_update()
