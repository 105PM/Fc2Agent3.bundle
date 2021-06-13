# -*- coding: utf-8 -*-
# FC2 Agent v3 by 105PM

import os, traceback, re, json, unicodedata, urllib

def Start():
    HTTP.CacheTime = 0

    
def change_html( text):
    if text is not None:
        return text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&#35;', '#').replace('&#39;', "‘")


def send_search(keyword, manual, year=''):
    try:
        url = '{ddns}/mod/api/fc2metadata/search?keyword={keyword}&manual={manual}&year={year}&call=plex&apikey={apikey}'.format(
            ddns=Prefs['sjva_url'],
            keyword=urllib.quote(keyword.encode('utf8')),
            manual=manual,
            year=year,
            apikey=Prefs['sjva_apikey']
        )
        Log(url)
        return my_JSON_ObjectFromURL(url)

    except Exception as e: 
        Log('Exception:%s', e)
        Log(traceback.format_exc())


def send_info(code, title=None):
    try:
        url = '{ddns}/mod/api/fc2metadata/info?code={code}&call=plex&apikey={apikey}'.format(
            ddns=Prefs['sjva_url'],
            code=urllib.quote(code.encode('utf8')),
            apikey=Prefs['sjva_apikey']
        )
        # if title is not None:
        #     url += '&title=' + urllib.quote(title.encode('utf8'))
        Log(url)
        return my_JSON_ObjectFromURL(url)

    except Exception as e: 
        Log('Exception:%s', e)
        Log(traceback.format_exc())



def my_JSON_ObjectFromURL(url, timeout=None, retry=3):
    try:
        if timeout is None:
            timeout = int(Prefs['timeout'])
        Log('my_JSON_ObjectFromURL retry : %s, url : %s', retry, url)
        return JSON.ObjectFromURL(url, timeout=timeout)
    except Exception as e: 
        Log('Exception:%s', e)
        Log(traceback.format_exc())
        if retry > 0:
            time.sleep(1)
            Log('RETRY : %s', retry)
            return my_JSON_ObjectFromURL(url, timeout, retry=(retry-1))
        else:
            Log('CRITICAL my_JSON_ObjectFromURL error')


def get_search_keyword(media, manual, from_file=False):
    try:
        
        if manual:
            ret = unicodedata.normalize('NFKC', unicode(media.name)).strip()

        else:
            if from_file:
                data = my_JSON_ObjectFromURL('http://127.0.0.1:32400/library/metadata/%s' % media.id)
                filename = data['MediaContainer']['Metadata'][0]['Media'][0]['Part'][0]['file']
                ret = os.path.splitext(os.path.basename(filename))[0]
                ret = re.sub('\s*\[.*?\]', '', ret).strip()
                match = Regex(r'(?P<cd>cd\d{1,2})$').search(ret) 
                if match:
                    ret = ret.replace(match.group('cd'), '')
            
            else:
                # from_scanner
                ret = media.name
        Log(ret)
        return ret

    except Exception as e: 
        Log('Exception:%s', e)
        Log(traceback.format_exc())


def base_search(results, media, lang, manual, keyword):
    data = send_search(keyword, manual)
    for item in data:
        Log(item)
        #title = '[%s]%s' % (item['ui_code'], String.DecodeHTMLEntities(String.StripTags(item['title_ko'])).strip())
        if item['year'] != '' and item['year'] is not None:
            title = '{} / {} / {}'.format(item['ui_code'], item['year'], item['site'])
            year = item['year']
        else:
            title = '{} / {}'.format(item['ui_code'], item['site'])
            year = ''
        meta = MetadataSearchResult(id=item['code'], name=title, year=year, score=item['score'], thumb=item['image_url'], lang=lang)
        meta.summary = change_html(item['title_ko'])
        meta.type = "movie"
        results.Append(meta)


def base_update(metadata, media, lang):
    Log("UPDATE : %s" % metadata.id)
    data = send_info(metadata.id)

    metadata.title = change_html(data['title'])
    metadata.original_title = metadata.title_sort = data['originaltitle']
    try: metadata.year = data['year']
    except: pass
    try: metadata.duration = data['runtime']*60
    except: pass
    try: metadata.studio = data['studio']
    except: pass
    metadata.summary = change_html(data['plot'])

    if 'premiered' in data and data['premiered'] is not None and len(data['premiered']) == 10 and data['premiered'] != '0000-00-00':
        metadata.originally_available_at = Datetime.ParseDate(data['premiered']).date()
    metadata.countries = data['country']
    metadata.tagline = change_html(data['tagline'])
    metadata.content_rating = data['mpaa']
    try:
        if data['ratings'] is not None and len(data['ratings']) > 0:
            if data['ratings'][0]['max'] == 5:
                metadata.rating = float(data['ratings'][0]['value']) * 2
                #metadata.rating_image= data['ratings'][0]['image_url']
                #metadata.rating_image = 'imdb://image.rating'
                #metadata.audience_rating = float(data['ratings'][0]['value']) * 2
                #metadata.audience_rating_image = 'rottentomatoes://image.rating.upright'

    except Exception as exception: 
        Log('Exception:%s', exception)
        Log(traceback.format_exc())

    ProxyClass = Proxy.Preview 
    landscape = None
    for item in data['thumb']:
        if item['aspect'] == 'poster':
            try: metadata.posters[item['value']] = ProxyClass(HTTP.Request(item['value']).content, sort_order=10)
            except: pass
        if item['aspect'] == 'landscape':
            landscape = item['value']
            try: metadata.art[item['value']] = ProxyClass(HTTP.Request(item['value']).content, sort_order=10)
            except: pass

    if data['fanart'] is not None:
        for item in data['fanart']:
            try: metadata.art[item] = ProxyClass(HTTP.Request(item).content)
            except: pass

    if data['genre'] is not None:
        metadata.genres.clear()
        for item in data['genre']:
            metadata.genres.add(item)

    if data['tag'] is not None:
        metadata.collections.clear()
        for item in data['tag']:
            metadata.collections.add(change_html(item))

    if data['director'] is not None:
        metadata.directors.clear()
        meta_director = metadata.directors.new()
        meta_director.name = data['director']

    if data['actor'] is not None:
        metadata.roles.clear()
        for item in data['actor']:
            actor = metadata.roles.new()
            actor.role = item['originalname']
            actor.name = item['name']
            actor.photo = item['thumb']

    # if data['extras'] is not None:
    #     for item in data['extras']:
    #         if item['mode'] == 'mp4':
    #             url = 'sjva://sjva.me/video.mp4/%s' % item['content_url']
    #         metadata.extras.add(TrailerObject(url=url, title=self.change_html(data['extras'][0]['title']), originally_available_at=metadata.originally_available_at, thumb=landscape))
    return


class Fc2Agent3(Agent.Movies):
    name = 'FC2 Agent v3'
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']
    languages = [Locale.Language.Korean]

    def search(self, results, media, lang, manual):
        keyword = get_search_keyword(media, manual, from_file=True)
        keyword = keyword.replace(' ', '-')
        base_search(results, media, lang, manual, keyword)
 

    def update(self, metadata, media, lang):
        base_update(metadata, media, lang)