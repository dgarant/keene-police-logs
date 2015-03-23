from bs4 import BeautifulSoup, SoupStrainer
import requests
import requests_cache
import re
import os

requests_cache.install_cache("log_cache")
rcache = requests_cache.get_cache()

# these pages represent yearly archives
yearly_archive_pages = [
    "http://www.ci.keene.nh.us/node/362",
    "http://www.ci.keene.nh.us/node/89312",
    "http://www.ci.keene.nh.us/node/88748",
    "http://www.ci.keene.nh.us/node/90175",
    "http://www.ci.keene.nh.us/node/90489",
    "http://www.ci.keene.nh.us/node/90805",
    "http://www.ci.keene.nh.us/node/90174",
]


def main():
    for page in yearly_archive_pages:
        page_resp = requests.get(page)
        soup = BeautifulSoup(page_resp.text, parse_only=SoupStrainer('a'))
        for link in soup.find_all("a", href=re.compile(".*\.pdf")):
            if not "http" in link["href"]:
                url = "http://www.ci.keene.nh.us" + link["href"]
            else:
                url = link["href"]

            with open("pdfs/{0}".format(os.path.basename(url)), "wb") as handle:
                handle.write(requests.get(url).content)

if __name__ == "__main__":
    main()
