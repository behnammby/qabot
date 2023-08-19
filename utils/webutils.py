import validators
from typing import List, Set
from playwright.sync_api import sync_playwright, Page
from urllib.parse import urlparse
from url_normalize import url_normalize
from os import path
import logging


def normalize(url: str) -> str:
    n_start_url = str(url_normalize(url))
    n_start_url = n_start_url.strip("/").lower()

    return str(n_start_url)


def extract_page_url(page: Page, allowed_domains: List[str]):
    urls: Set[str] = set()

    page_url = urlparse(page.url)

    links = page.query_selector_all("a")
    # logging.info(f"{len(links)} links found")
    for link in links:
        href = ""
        try:
            href = link.get_attribute("href")
        except Exception as exp:
            logging.warning(f"couldn't get link attribute: {exp}")
            continue

        if href is None:
            continue

        if href.startswith("/"):
            href = page_url.scheme + "://" + page_url.netloc + href

        if validators.url(href) != True:
            continue

        # logging.info(f"checking {href}...")
        url = urlparse(href)

        # logging.info(f"domain of link is {url.netloc}")
        if url.netloc not in allowed_domains:
            # logging.info("skipping...")
            continue

        # logging.info(f"normalizing...")
        n_url = normalize(str(url.geturl()))

        if n_url == "":
            # logging.info("normalized is empty, skipping...")
            continue

        if n_url not in urls:
            urls.add(n_url)

    return urls


def process(id: int, url: str, allowed_domains: List[str], output: str):
    logging.info(f"processing id= {id}, url= {url} started")

    urls: Set[str] = set()
    result: str = ""
    doc: str = ""
    failed: bool = False

    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page()

        try:
            page.set_default_navigation_timeout(30_000)

            logging.info(f"navigating to url {url}")
            page.goto(url)

            logging.info("navigated")

            doc = page.content()
        except Exception as exp:
            failed = True
            result = f"couldn't navigate to url {url}: {exp}"

        if failed == False:
            if len(doc) > 0:
                logging.info(f"document length is {len(doc)}")

                logging.info(f"extracting links...")
                urls = extract_page_url(page, allowed_domains)

                logging.info(f"{len(urls)} valid urls found")

                file_name = f"page_{id}.html"
                logging.info(f"saving to {file_name}...")

                try:
                    with open(path.join(output, file_name), "w") as f:
                        f.write(doc)

                    result = "saved successfully"
                except Exception as exp:
                    failed = True
                    result = f"not saved with error: {exp}"
            else:
                failed = True
                result = "page has no content"

        browser.close()

    logging.info(f"finished with result= {result}")
    return failed, urls, result
