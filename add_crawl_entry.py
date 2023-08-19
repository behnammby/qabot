import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "crawler"))

os.environ.setdefault("DATABASE", "mysql://sin:873gd6tdsh782tdgygw@chat.aibaazar.com:3306/gpt")
from crawler.crawl import Crawl

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("no urls passed")

        exit(1)

    output = sys.argv[1]
    url = sys.argv[2]
    allowed_domains = sys.argv[3:]

    # process(start_url=url, allowed_domains=allowed_domains, output=output)

    crawl = Crawl()

    print(f"adding new entry for project {output} and {url} added to database.")
    result = crawl.add_new_scrape(output, url, allowed_domains)
    if result:
        print("added.")
    else:
        print(f"failed.")
