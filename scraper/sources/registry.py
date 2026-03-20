"""
Registry of all standard RSS sources.
Each entry uses make_scraper() from base.py.
Import REGISTRY in main.py instead of individual source files.
"""
from sources.base import make_scraper

REGISTRY = {
    "aljazeera": make_scraper("Al Jazeera", [
        "https://www.aljazeera.com/xml/rss/all.xml",
    ]),
    "ars": make_scraper("Ars Technica", [
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://feeds.arstechnica.com/arstechnica/science",
        "https://feeds.arstechnica.com/arstechnica/tech-policy",
    ]),
    "billboard": make_scraper("Billboard", [
        "https://www.billboard.com/feed/",
        "https://www.billboard.com/music/chart-beat/feed/",
    ]),
    "cbs": make_scraper("CBS News", [
        "https://www.cbsnews.com/latest/rss/main",
        "https://www.cbsnews.com/latest/rss/us",
        "https://www.cbsnews.com/latest/rss/world",
        "https://www.cbsnews.com/latest/rss/politics",
        "https://www.cbsnews.com/latest/rss/health",
        "https://www.cbsnews.com/latest/rss/moneywatch",
        "https://www.cbsnews.com/latest/rss/technology",
        "https://www.cbsnews.com/latest/rss/science",
        "https://www.cbsnews.com/latest/rss/entertainment",
    ]),
    "cbssports": make_scraper("CBS Sports", [
        "https://www.cbssports.com/rss/headlines/",
        "https://www.cbssports.com/rss/headlines/nfl/",
        "https://www.cbssports.com/rss/headlines/nba/",
        "https://www.cbssports.com/rss/headlines/mlb/",
    ]),
    "cnbc": make_scraper("CNBC", [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "https://www.cnbc.com/id/15839135/device/rss/rss.html",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "https://www.cnbc.com/id/100727362/device/rss/rss.html",
        "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "https://www.cnbc.com/id/10000115/device/rss/rss.html",
        "https://www.cnbc.com/id/10000108/device/rss/rss.html",
    ]),
    "cnet": make_scraper("CNET", [
        "https://www.cnet.com/rss/news/",
        "https://www.cnet.com/rss/tech/",
    ]),
    "cos": make_scraper("Consequence of Sound", [
        "https://consequence.net/feed/",
        "https://consequence.net/category/news/feed/",
    ]),
    "deadline": make_scraper("Deadline", [
        "https://deadline.com/feed/",
        "https://deadline.com/category/film/feed/",
        "https://deadline.com/category/tv/feed/",
    ]),
    "deadspin": make_scraper("Deadspin", [
        "https://deadspin.com/rss",
    ]),
    "engadget": make_scraper("Engadget", [
        "https://www.engadget.com/rss.xml",
    ]),
    "espn": make_scraper("ESPN", [
        "https://www.espn.com/espn/rss/news",
        "https://www.espn.com/espn/rss/nfl/news",
        "https://www.espn.com/espn/rss/nba/news",
        "https://www.espn.com/espn/rss/mlb/news",
        "https://www.espn.com/espn/rss/nhl/news",
    ]),
    "eurogamer": make_scraper("Eurogamer", [
        "https://www.eurogamer.net/?format=rss",
    ]),
    "euronews": make_scraper("Euronews", [
        "https://feeds.feedburner.com/euronews/en/home",
        "https://feeds.feedburner.com/euronews/en/news/world",
    ]),
    "fiercehealthcare": make_scraper("Fierce Healthcare", [
        "https://www.fiercehealthcare.com/rss/xml/",
    ]),
    "forbes": make_scraper("Forbes", [
        "https://www.forbes.com/real-time/feed2/",
        "https://www.forbes.com/innovation/feed2/",
        "https://www.forbes.com/business/feed2/",
    ]),
    "fortune": make_scraper("Fortune", [
        "https://fortune.com/feed/",
        "https://fortune.com/section/tech/feed/",
        "https://fortune.com/section/finance/feed/",
    ]),
    "france24": make_scraper("France 24", [
        "https://www.france24.com/en/rss",
        "https://www.france24.com/en/asia-pacific/rss",
        "https://www.france24.com/en/europe/rss",
        "https://www.france24.com/en/middle-east/rss",
        "https://www.france24.com/en/americas/rss",
    ]),
    "gamespot": make_scraper("GameSpot", [
        "https://www.gamespot.com/feeds/mashup/",
        "https://www.gamespot.com/feeds/news/",
    ]),
    "gizmodo": make_scraper("Gizmodo", [
        "https://gizmodo.com/rss",
        "https://gizmodo.com/tech/rss",
    ]),
    "guardian": make_scraper("The Guardian", [
        "https://www.theguardian.com/world/rss",
        "https://www.theguardian.com/us-news/rss",
        "https://www.theguardian.com/uk-news/rss",
        "https://www.theguardian.com/technology/rss",
        "https://www.theguardian.com/science/rss",
        "https://www.theguardian.com/business/rss",
        "https://www.theguardian.com/sport/rss",
        "https://www.theguardian.com/culture/rss",
    ]),
    "guardianenv": make_scraper("The Guardian (Environment)", [
        "https://www.theguardian.com/environment/rss",
        "https://www.theguardian.com/environment/climate-change/rss",
    ]),
    "ign": make_scraper("IGN", [
        "https://feeds.ign.com/ign/all",
        "https://feeds.ign.com/ign/game-reviews",
    ]),
    "independent": make_scraper("The Independent", [
        "https://www.independent.co.uk/news/rss",
        "https://www.independent.co.uk/news/world/rss",
        "https://www.independent.co.uk/news/uk/rss",
    ]),
    "insideclimate": make_scraper("Inside Climate News", [
        "https://insideclimatenews.org/feed/",
    ]),
    "kffhealth": make_scraper("KFF Health News", [
        "https://kffhealthnews.org/feed/",
    ]),
    "kotaku": make_scraper("Kotaku", [
        "https://kotaku.com/rss",
    ]),
    "livescience": make_scraper("LiveScience", [
        "https://www.livescience.com/feeds/all",
    ]),
    "macrumors": make_scraper("MacRumors", [
        "https://feeds.macrumors.com/MacRumors-All",
    ]),
    "marketwatch": make_scraper("MarketWatch", [
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://feeds.marketwatch.com/marketwatch/marketpulse/",
    ]),
    "medpage": make_scraper("MedPage Today", [
        "https://www.medpagetoday.com/rss/headlines.xml",
    ]),
    "mittech": make_scraper("MIT Technology Review", [
        "https://www.technologyreview.com/feed/",
    ]),
    "nasa": make_scraper("NASA", [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss",
    ]),
    "newscientist": make_scraper("New Scientist", [
        "https://www.newscientist.com/feed/home/",
    ]),
    "newsweek": make_scraper("Newsweek", [
        "https://www.newsweek.com/rss",
        "https://www.newsweek.com/rss/us-news",
        "https://www.newsweek.com/rss/world",
    ]),
    "nme": make_scraper("NME", [
        "https://www.nme.com/feed",
    ]),
    "9to5google": make_scraper("9to5Google", [
        "https://9to5google.com/feed/",
    ]),
    "9to5mac": make_scraper("9to5Mac", [
        "https://9to5mac.com/feed/",
    ]),
    "pcgamer": make_scraper("PC Gamer", [
        "https://www.pcgamer.com/rss/",
    ]),
    "people": make_scraper("People", [
        "https://people.com/feed/",
    ]),
    "physorg": make_scraper("Phys.org", [
        "https://phys.org/rss-feed/",
    ]),
    "pitchfork": make_scraper("Pitchfork", [
        "https://pitchfork.com/feed/feed-news/rss",
    ]),
    "polygon": make_scraper("Polygon", [
        "https://www.polygon.com/rss/index.xml",
    ]),
    "popsci": make_scraper("Popular Science", [
        "https://www.popsci.com/feed/",
    ]),
    "register": make_scraper("The Register", [
        "https://www.theregister.com/headlines.atom",
    ]),
    "rollingstone": make_scraper("Rolling Stone", [
        "https://www.rollingstone.com/feed/",
    ]),
    "rps": make_scraper("Rock Paper Shotgun", [
        "https://www.rockpapershotgun.com/feed",
    ]),
    "sciencealert": make_scraper("ScienceAlert", [
        "https://www.sciencealert.com/feed",
    ]),
    "sciencedaily": make_scraper("Science Daily", [
        "https://www.sciencedaily.com/rss/all.xml",
    ]),
    "sciencenews": make_scraper("Science News", [
        "https://www.sciencenews.org/feed",
    ]),
    "scmp": make_scraper("South China Morning Post", [
        "https://www.scmp.com/rss/91/feed",
        "https://www.scmp.com/rss/2/feed",
    ]),
    "skynews": make_scraper("Sky News", [
        "https://feeds.skynews.com/feeds/rss/home.xml",
        "https://feeds.skynews.com/feeds/rss/world.xml",
        "https://feeds.skynews.com/feeds/rss/us.xml",
    ]),
    "smithsonian": make_scraper("Smithsonian Magazine", [
        "https://www.smithsonianmag.com/rss/latest_articles/",
    ]),
    "space": make_scraper("Space.com", [
        "https://www.space.com/feeds/all",
    ]),
    "statnews": make_scraper("STAT News", [
        "https://www.statnews.com/feed/",
    ]),
    "stereogum": make_scraper("Stereogum", [
        "https://www.stereogum.com/feed/",
    ]),
    "atlantic": make_scraper("The Atlantic", [
        "https://www.theatlantic.com/feed/all/",
    ]),
    "techcrunch": make_scraper("TechCrunch", [
        "https://techcrunch.com/feed/",
        "https://techcrunch.com/category/startups/feed/",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
    ]),
    "variety": make_scraper("Variety", [
        "https://variety.com/feed/",
    ]),
    "venturebeat": make_scraper("VentureBeat", [
        "https://venturebeat.com/feed/",
    ]),
    "vox": make_scraper("Vox", [
        "https://www.vox.com/rss/index.xml",
    ]),
    "wired": make_scraper("Wired", [
        "https://www.wired.com/feed/rss",
    ]),
    "yahoosports": make_scraper("Yahoo Sports", [
        "https://sports.yahoo.com/rss/",
    ]),
    "yalee360": make_scraper("Yale Environment 360", [
        "https://e360.yale.edu/feed",
    ]),
    "carbonbrief": make_scraper("Carbon Brief", [
        "https://www.carbonbrief.org/feed/",
        "https://feeds.feedburner.com/CarbonBrief",
    ]),
    "grist": make_scraper("Grist", [
        "https://grist.org/feed/",
    ]),
    "hollywoodreporter": make_scraper("Hollywood Reporter", [
        "https://www.hollywoodreporter.com/feed/",
    ]),
    "pagesix": make_scraper("Page Six", [
        "https://pagesix.com/feed/",
        "https://pagesix.com/category/entertainment/feed/",
    ]),
    "enews": make_scraper("E! News", [
        "https://www.eonline.com/syndication/feeds/rss/topstories.xml",
    ]),
}
