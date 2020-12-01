# Gemini News Reader (serverless version)

## How it works
* crawler.py searches specific news sites to convert content into a gemini-readable format
    * I'm using Firefox's *Readability.js* to get the HTML equivalent, and then using LukeEmmet's *html2gmi* to convert it to text/gemini
    * These sites are saved, listed in the file news.gmi, and are updated on their next request if more than a week old

## How can I run my own?
If you want to create your own gemini news feed, go ahead! However, I created this specifically for my own needs, so this *may* not be exactly what you're looking for.

* Clone this Github repo
* cd inside and run `npm install` (must have node.js and npm installed)
* run `pip3 install -r requirements.txt`
* run the crawler with `python3 crawler.py`
    * change how many articles you want to store max with `MAX_SAVED_ARTILCES`
    * change the file path where you save the index page and articles with `GEM_PATH`
* This version fetches articles from NPR and CNN text-only pages. The full versions of these sites
  should work fine, but the advantage here is that less data is used. You can add another site to be
  indexed by modifying urls_linkPath
