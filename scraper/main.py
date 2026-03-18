"""
News Bites — Scraper
Usage:
    python main.py                        # scrape all sources, save to output/articles.json
    python main.py --limit 10             # cap at 10 articles per source
    python main.py --source nbc           # only run NBC News
    python main.py --out my_file.json     # custom output path
"""

import argparse
import json
import os
from datetime import datetime, timezone

from sources.abc_news import scrape as scrape_abc
from sources.al_jazeera import scrape as scrape_aljazeera
from sources.ap_news import scrape as scrape_ap
from sources.ars_technica import scrape as scrape_ars
from sources.axios import scrape as scrape_axios
from sources.bbc_news import scrape as scrape_bbc
from sources.cbs_news import scrape as scrape_cbs
from sources.cnbc import scrape as scrape_cnbc
from sources.cnn import scrape as scrape_cnn
from sources.deutsche_welle import scrape as scrape_dw
from sources.espn import scrape as scrape_espn
from sources.fox_news import scrape as scrape_fox
from sources.france24 import scrape as scrape_france24
from sources.nbc_news import scrape as scrape_nbc
from sources.npr import scrape as scrape_npr
from sources.the_guardian import scrape as scrape_guardian
from sources.the_hill import scrape as scrape_hill
from sources.washington_post import scrape as scrape_wapo
from sources.billboard import scrape as scrape_billboard
from sources.business_insider import scrape as scrape_business_insider
from sources.cbs_sports import scrape as scrape_cbs_sports
from sources.cnet import scrape as scrape_cnet
from sources.deadline import scrape as scrape_deadline
from sources.e_news import scrape as scrape_e_news
from sources.engadget import scrape as scrape_engadget
from sources.gamespot import scrape as scrape_gamespot
from sources.gizmodo import scrape as scrape_gizmodo
from sources.guardian_environment import scrape as scrape_guardian_env
from sources.hollywood_reporter import scrape as scrape_hollywood_reporter
from sources.ign import scrape as scrape_ign
from sources.inside_climate_news import scrape as scrape_inside_climate
from sources.kff_health_news import scrape as scrape_kff_health
from sources.kotaku import scrape as scrape_kotaku
from sources.new_scientist import scrape as scrape_new_scientist
from sources.phys_org import scrape as scrape_phys_org
from sources.livescience import scrape as scrape_livescience
from sources.marketwatch import scrape as scrape_marketwatch
from sources.page_six import scrape as scrape_page_six
from sources.people import scrape as scrape_people
from sources.pitchfork import scrape as scrape_pitchfork
from sources.polygon import scrape as scrape_polygon
from sources.popular_science import scrape as scrape_popular_science
from sources.rolling_stone import scrape as scrape_rolling_stone
from sources.science_daily import scrape as scrape_science_daily
from sources.science_news import scrape as scrape_science_news
from sources.smithsonian_mag import scrape as scrape_smithsonian
from sources.space_com import scrape as scrape_space
from sources.tmz import scrape as scrape_tmz
from sources.stat_news import scrape as scrape_stat_news
from sources.techcrunch import scrape as scrape_techcrunch
from sources.the_verge import scrape as scrape_verge
from sources.variety import scrape as scrape_variety
from sources.venturebeat import scrape as scrape_venturebeat
from sources.wired import scrape as scrape_wired
from sources.yahoo_sports import scrape as scrape_yahoo_sports
from sources.vox import scrape as scrape_vox
from sources.newsweek import scrape as scrape_newsweek
from sources.sky_news import scrape as scrape_sky_news
from sources.euronews import scrape as scrape_euronews
from sources.the_independent import scrape as scrape_independent
from sources.south_china_morning_post import scrape as scrape_scmp
from sources.the_atlantic import scrape as scrape_atlantic
from sources.forbes import scrape as scrape_forbes
from sources.fortune import scrape as scrape_fortune
from sources.mit_tech_review import scrape as scrape_mit_tech
from sources.nine_to_five_mac import scrape as scrape_9to5mac
from sources.macrumors import scrape as scrape_macrumors
from sources.the_register import scrape as scrape_register
from sources.pc_gamer import scrape as scrape_pc_gamer
from sources.rock_paper_shotgun import scrape as scrape_rps
from sources.eurogamer import scrape as scrape_eurogamer
from sources.nasa import scrape as scrape_nasa
from sources.nme import scrape as scrape_nme
from sources.consequence_of_sound import scrape as scrape_cos
from sources.stereogum import scrape as scrape_stereogum
from sources.medpage_today import scrape as scrape_medpage
from sources.fierce_healthcare import scrape as scrape_fierce_health
from sources.grist import scrape as scrape_grist
from sources.carbon_brief import scrape as scrape_carbon_brief
from sources.yale_environment_360 import scrape as scrape_yale_e360

SOURCES = {
    # General / US News
    "nbc": scrape_nbc,
    "abc": scrape_abc,
    "cbs": scrape_cbs,
    "cnn": scrape_cnn,
    "fox": scrape_fox,
    "ap": scrape_ap,
    "npr": scrape_npr,
    "axios": scrape_axios,
    "vox": scrape_vox,
    "newsweek": scrape_newsweek,
    "atlantic": scrape_atlantic,
    # World News
    "bbc": scrape_bbc,
    "guardian": scrape_guardian,
    "aljazeera": scrape_aljazeera,
    "dw": scrape_dw,
    "france24": scrape_france24,
    "skynews": scrape_sky_news,
    "euronews": scrape_euronews,
    "independent": scrape_independent,
    "scmp": scrape_scmp,
    # Politics
    "wapo": scrape_wapo,
    "hill": scrape_hill,
    # Business
    "cnbc": scrape_cnbc,
    "marketwatch": scrape_marketwatch,
    "businessinsider": scrape_business_insider,
    "forbes": scrape_forbes,
    "fortune": scrape_fortune,
    # Tech
    "wired": scrape_wired,
    "ars": scrape_ars,
    "verge": scrape_verge,
    "techcrunch": scrape_techcrunch,
    "engadget": scrape_engadget,
    "cnet": scrape_cnet,
    "venturebeat": scrape_venturebeat,
    "gizmodo": scrape_gizmodo,
    "mittech": scrape_mit_tech,
    "9to5mac": scrape_9to5mac,
    "macrumors": scrape_macrumors,
    "register": scrape_register,
    # Science
    "popsci": scrape_popular_science,
    "space": scrape_space,
    "livescience": scrape_livescience,
    "sciencedaily": scrape_science_daily,
    "physorg": scrape_phys_org,
    "smithsonian": scrape_smithsonian,
    "sciencenews": scrape_science_news,
    "newscientist": scrape_new_scientist,
    "nasa": scrape_nasa,
    # Sports
    "espn": scrape_espn,
    "cbssports": scrape_cbs_sports,
    "yahoosports": scrape_yahoo_sports,
    # Entertainment
    "tmz": scrape_tmz,
    "people": scrape_people,
    "enews": scrape_e_news,
    "pagesix": scrape_page_six,
    "variety": scrape_variety,
    "hollywoodreporter": scrape_hollywood_reporter,
    "deadline": scrape_deadline,
    # Gaming
    "ign": scrape_ign,
    "kotaku": scrape_kotaku,
    "polygon": scrape_polygon,
    "gamespot": scrape_gamespot,
    "pcgamer": scrape_pc_gamer,
    "rps": scrape_rps,
    "eurogamer": scrape_eurogamer,
    # Music
    "pitchfork": scrape_pitchfork,
    "rollingstone": scrape_rolling_stone,
    "billboard": scrape_billboard,
    "nme": scrape_nme,
    "cos": scrape_cos,
    "stereogum": scrape_stereogum,
    # Health
    "statnews": scrape_stat_news,
    "kffhealth": scrape_kff_health,
    "medpage": scrape_medpage,
    "fiercehealthcare": scrape_fierce_health,
    # Climate
    "insideclimate": scrape_inside_climate,
    "guardianenv": scrape_guardian_env,
    "grist": scrape_grist,
    "carbonbrief": scrape_carbon_brief,
    "yalee360": scrape_yale_e360,
}


def parse_args():
    parser = argparse.ArgumentParser(description="News Bites scraper")
    parser.add_argument("--limit", type=int, default=None, help="Max articles per source")
    parser.add_argument("--source", choices=list(SOURCES.keys()), help="Run a single source")
    parser.add_argument("--out", type=str, default=None, help="Output file path (default: output/YYYY-MM-DD.json)")
    return parser.parse_args()


def main():
    args = parse_args()

    sources_to_run = (
        {args.source: SOURCES[args.source]} if args.source else SOURCES
    )

    all_articles = []
    for _, scrape_fn in sources_to_run.items():
        articles = scrape_fn(limit=args.limit)
        all_articles.extend(articles)

    print(f"\nTotal articles scraped: {len(all_articles)}")

    # Determine output path
    if args.out:
        out_path = args.out
    else:
        os.makedirs("output", exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = f"output/{date_str}.json"

    with open(out_path, "w") as f:
        json.dump(all_articles, f, indent=2)

    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
