from model import Scrape
from peewee import IntegrityError,fn
from typing import List


class Crawl:
    def __init__(self) -> None:
        pass

    def add_new_scrape(self, project: str, url: str, allowed_domains: str) -> bool:
        scrape = Scrape(project=project, url=url,
                        allowed_domains=allowed_domains)

        try:
            scrape.save()
        except IntegrityError:
            return False
        return True

    def get_unprocessed_scrapes(self, limit: int) -> List[Scrape]:
        scrapes = Scrape.select().where(Scrape.processed == False).order_by(fn.Rand()).limit(limit)

        return scrapes
