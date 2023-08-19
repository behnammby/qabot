import os
import sys
import logging
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "crawler"))

os.environ.setdefault("DATABASE", "mysql://sin:873gd6tdsh782tdgygw@178.63.138.182:3306/gpt")
from crawler.crawl import Crawl
from utils.webutils import process

logging.getLogger().setLevel(logging.INFO)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("no urls passed")

        exit(1)

    limit = sys.argv[1]
    output = sys.argv[2]

    crawl = Crawl()

    index = 0
    while True:
        index += 1
        logging.info(f"getting unprocessed scrapes, round {index}...")
        scrapes = crawl.get_unprocessed_scrapes(int(limit))

        if len(scrapes) == 0:
            logging.info("all scrapes processed.")
            break

        logging.info(f"{len(scrapes)} unprocessed scrapes got")

        for scrape in scrapes:
            print(f"scraping id= {scrape.id}, project= {scrape.project}, url= {scrape.url}")
            failed, new_urls, result = process(scrape.id, scrape.url, scrape.allowed_domains, f"{output}/{scrape.project}")

            scrape.failed = failed
            scrape.processed = True
            scrape.result = result

            try:
                scrape.save()
            except Exception as exp:
                logging.info(f"couldn't update scrape with error: {exp}")

            logging.info("scraping finished.")

            logging.info(f"now adding {len(new_urls)} urls found in the page")
            added = 0
            for url in new_urls:
                if crawl.add_new_scrape(scrape.project, url, scrape.allowed_domains):
                    added += 1

            logging.info(f"{added} out of {len(new_urls)} added to db.")
            time.sleep(5)

        time.sleep(60)

        
        
