from bs4 import BeautifulSoup as soup
import requests, os, re, sqlite3, subprocess
from urllib.parse import urlparse
from datetime import datetime
import hashlib

MAX_SAVED_ARTICLES = 100
GEMPATH = '/home/pine/public_gemini/'
urls_linkPath = {"NPR": {"https://text.npr.org/": 'body div.topic-container ul li a'}, "CNN": {'http://lite.cnn.com/en': 'body div ul li a'},} #"Christian Science Monitor": {'https://www.csmonitor.com/layout/set/text/textedition': 'body div#csm-page-content ul li a.ezc-csm-story-link'}}

def hash_bytestr_iter(bytesiter, hasher, ashexstr=False):
    for block in bytesiter:
        hasher.update(block.encode())
    return hasher.hexdigest() if ashexstr else hasher.digest()

def split_string(string, blocksize=65536):
    return [string[i:i+blocksize] for i in range(0, len(string), blocksize)]

def get_hash(s):
    return hashlib.md5(s.encode()).hexdigest()

def process_input(url=None, html=None, display=None):
    try:
        ps = ""
        if html:
            ps = subprocess.Popen(('node', 'reader.js', 'html', html), stdout=subprocess.PIPE)
        elif url:
            ps = subprocess.Popen(('node', 'reader.js', 'url', url), stdout=subprocess.PIPE)
        output = subprocess.check_output(('./html2gmi', '-m', '-e', '-l', '1000'), stdin=ps.stdout)
        body = output.decode('UTF-8')
        if body == 'not readable\n' or body == 'error\n':
            return None

        now = datetime.now()
        header = ("Gemini News Reader\nAccessed at %s\n" % now.replace(microsecond=0).isoformat())
        if display:
            header += display + "\n"
        header += "-" * 31 + "\n"

        if display and url:
            f = open(GEMPATH + "articles/%s-%s.gmi" % (get_hash(url), now.timestamp()), "w")
            f.write(header + body)
            f.close()
            name = f.name.split("/")[1]

        #This might've been updating a file, in which case it's important to delete the old file, and update the database
        search = [i for i in next(os.walk(GEMPATH + 'articles'))[2] if i[:32]==get_hash(url)]
        if len(search)>1:
            for f in search[:-1]: #only remove the older ones (there should be only one, but idk)
                os.remove(GEMPATH + 'articles/' + f)
                print("deleting old file, " + f)
            cursor.execute("UPDATE article set date = ?, filename = ? WHERE url = ?",(now.replace(microsecond=0).isoformat(), search[-1], url))
            connection.commit()
        if display and url:
            return [header + body, name]
        else:
            return header + body
    except Exception as e:
        print(e)
        return None
if not os.path.exists(GEMPATH + 'articles'):
    os.makedirs(GEMPATH + 'articles')
connection = sqlite3.connect(GEMPATH + "articles/articles.db")
cursor = connection.cursor()
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
if not(tables and len(tables) > 0 and 'article' in tables[0]):
    cursor.execute("CREATE TABLE article (filename TEXT, url TEXT, source TEXT, title TEXT, date TEXT, md5sum TEXT)")
    connection.commit()

for name, url_linkPath in urls_linkPath.items():
    for url, linkPath in url_linkPath.items():
        print(name)
        p_url = urlparse(url)
        html = requests.get(url).text
        a_list = soup(html, 'html.parser').select(linkPath)

        skip_count = 0
        for a in a_list:
            if a.get("href"):
                try:
                    path = p_url.scheme + "://" + p_url.netloc + a['href']
                    page = requests.get(path).text
                    if name == "NPR":
                        page = re.sub("<header>(?:[\s\S]*)<\/header>", "", page, 1)
                    sum = hash_bytestr_iter(split_string(page), hashlib.md5(), True)
                    if cursor.execute("SELECT title FROM article where md5sum = ?", (sum,),).fetchall():
                        #ensure that it isn't already in the database
                        skip_count += 1
                        print("skipping article at path " + path)
                        if skip_count >=7:
                            break
                    else:
                        #get the content/filename and write the .gmi file
                        x = process_input(url=path, html=str(soup(page, 'html.parser')), display=name + " - " + a.text)
                        if len(x)>1 and not x is None:
                            #^only run this section if it outputs content, and a file
                            date = datetime.strftime(datetime.fromtimestamp(float(x[1][33:48])), '%Y-%m-%dT%H:%M:%S')
                            #add it into the database
                            search = cursor.execute("SELECT source, title FROM article where url = ? AND md5sum != ?", (path, sum,),).fetchall()
                            if search:
                                #^if the search found something, then the url is already in there, so we just have to update the sum, date, and name
                                cursor.execute("UPDATE article SET md5sum = ?, date = ?, title = ? WHERE url = ?",(sum, date, a.text, path,),)
                            else: 
                                cursor.execute("INSERT INTO article VALUES (?, ?, ?, ?, ?, ?)",(x[1], path, name, a.text, date, sum,),)
                            print("added article " + a.text)
                            connection.commit()
                         
                except Exception as e: 
                    print("the url " + a['href'] + " failed")
                    print(e)
                    continue

def clean_up():
    l = len(next(os.walk(GEMPATH + 'articles'))[2])
    l-= 1 #the article.db is in this folder, too
    if l > MAX_SAVED_ARTICLES:
        q = cursor.execute("SELECT filename from article ORDER BY date ASC").fetchall()[:l - MAX_SAVED_ARTICLES]
        #get the oldest articles that we're going to delete
        for f in [f[0] for f in q]:
            cursor.execute("DELETE FROM article WHERE filename = ?",(f,))
            os.remove(GEMPATH + 'articles/'+ f)
            print("deleted article " + f + " due to article cap")
            connection.commit()
    lines = ["# Gemini News Reader", "## Read today's articles:"]
    name_query = cursor.execute("SELECT filename, source, title, date FROM article WHERE date >= %s ORDER BY date DESC" % datetime.today().strftime("%Y-%m-%d")).fetchall()
    for i in name_query:
        if i[0] in saved:
            name = i[1] + " - " + i[2]
            lines.append("=>/articles/" + i[0] + " " + name)
    body = "\n".join(lines)

    index_page = open(GEMPATH + "news.gmi", "w")
    index_page.write(body)
    index_page.close()

    cursor.close()
    connection.close()

clean_up()
