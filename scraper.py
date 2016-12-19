# -*- coding: utf-8 -*-
import json
import re
import sqlite3
import urllib2
from bs4 import BeautifulSoup

domain_name = "papermag.com"
base_url = "http://papermag.com/"
proxy_host = "192.168.251.1"
proxy_port = "8080"
proxy_username = "0160092"
proxy_password = "016009297"

proxy_addr = proxy_username + ":" + proxy_password + "@" + proxy_host + ":" + proxy_port


def get_readable_text(non_readable):
    rt = re.sub('^[a-zA-Z0-9-_*. ]', '', non_readable.encode('utf-8'))

    return rt


def get_info(url):
    article_content = get_content_from_url(url)
    soup = BeautifulSoup(article_content, "lxml")

    title = get_readable_text(soup.find("div", {'class': "headline"}).text)

    text = ""
    for text_segment in soup.findAll("p"):
        text += get_readable_text(text_segment.text)

    author = get_readable_text(soup.find("a", {'class': "author-post__name"}).text)
    datetime = get_readable_text(soup.find("div", {'class': "author-post__date"}).text).split("at")

    date = datetime[0]
    time = datetime[1]

    print "GOT {0} \n".format(title)

    return {
        'title': title,
        'text': text,
        'author': author,
        'date': date,
        'time': time,
    }


def get_info_from_art_url_pack(category_articles_urls_pack, conn, table):
    for url_pack in category_articles_urls_pack:
        for url in url_pack:
            row = get_info(url)
            sqlite_insert(conn, table, row)


# def get_categories(content):
#     soup = BeautifulSoup(content, "lxml")
#     categories = []
#
#     for l in soup.findAll("div", {"class": "menu-global__section-links"}):
#         for tag_a in l.find_all("a"):
#             if re.findall(r'^/(\D+)$', tag_a["href"]):
#                 categories.append(tag_a["href"])
#
#     return categories


def get_content_from_url(url_):  # todo add proxy settings
    req = urllib2.Request(url_)
    res = urllib2.urlopen(req)

    return res.read()


def get_list_json_data(page, site_id, resource_id):
    return get_content_from_url(
        "https://www.papermag.com/core/load_more_posts/data.js?pn={page}&resource_id={resource_id}&site_id={site_id}".format(
            page=page, resource_id=resource_id, site_id=site_id))


def get_urls_from_long_list(url):
    art_by_cat = get_content_from_url(url)

    l = re.findall("site_id=(.*)&resource_id=(.*)'", art_by_cat)
    if len(l) == 0:
        print ("\tWarning! Can't find resource id and site id at url %s" % url)
        return []

    page_id = 0
    art_urls = []
    while True:
        raw_data = get_list_json_data(page_id, l[0][0], l[0][1])
        json_data = json.loads(raw_data)

        print ("\tPage number: {0}".format(page_id))
        for pbs in json_data["posts_by_source"]:
            if len(json_data["posts_by_source"][pbs]) == 0:
                break

            for key in json_data["posts_by_source"][pbs]:
                if isinstance(key, dict):
                    url = base_url + str(key["_id"]) + ".html"
                    # print ("\tAppended url: {0}".format(url))
                    art_urls.append(url)

        page_id += 1
        # break  # todo remove to parse all pages

    if len(art_urls) == 0:
        print "\tCan't get urls from %s" % url
    return art_urls


def sqlite_insert(conn, table, row):
    cols = ', '.join('"{}"'.format(col) for col in row.keys())
    vals = ', '.join(':{}'.format(col) for col in row.keys())
    sql = 'INSERT INTO "{0}" ({1}) VALUES ({2})'.format(table, cols, vals)
    conn.cursor().execute(sql, row)
    conn.commit()


def is_article(current_url):  # todo bug! not working
    return re.match(r"papermag.com\/[\w\-]{0,}[0-9]{10}\.html", current_url)


def make_pretty_url(url):  # todo add hostname, get short article url
    if re.match("^/", url):
        return base_url[:-1] + url

    return url


def has_base_domain(url):  # todo check!!!
    return re.match("(http|https)\:\/\/(www\.|)%s" % domain_name, url)


def get_all_urls(page_data):
    all_urls = []

    soup = BeautifulSoup(page_data, "lxml")
    for tag_a in soup.find_all("a"):
        if "href" not in tag_a.attrs:
            continue

        url = make_pretty_url(tag_a.attrs["href"])

        if has_base_domain(url):
            all_urls.append(url)

    return all_urls


def short_article_url(url):
    l = re.findall("([0-9]+\.html$)", url)
    if len(l) == 1:
        return base_url + l[0]

    return url


def start(connection, table):
    articles_urls = []
    parsed_urls = set()
    url_queue = set()
    url_queue.add(base_url)

    while len(url_queue) > 0:
        current_url = url_queue.pop()  # any from set
        print (current_url)
        print ("Size of set: " + str(len(url_queue)))

        if current_url in parsed_urls:
            continue

        parsed_urls.add(current_url)
        if is_article(current_url):
            articles_urls.append(current_url)

        page_data = get_content_from_url(current_url)
        next_urls = get_all_urls(page_data)
        next_urls += get_urls_from_long_list(current_url)
        for next_url in next_urls:
            next_url = short_article_url(next_url)
            if next_url in parsed_urls:
                continue

            url_queue.add(next_url)

    # get_info_from_art_url_pack(art_urls_all, connection, table)

    print("\n----------------------------------------\nAll data parsed!")


if __name__ == "__main__":
    sq_db_file = 'sq.sqlite3'

    table_name = 'articles'  # name of the table to be created
    id_column = 'id'  # name of the PRIMARY KEY column
    article_title = 'title'
    article_text = 'text'
    article_date = 'date'
    article_time = 'time'
    article_author = 'author'

    conn = sqlite3.connect(sq_db_file)
    conn.text_factory = str

    # conn.execute(
    #     "CREATE TABLE articles ({1} VARCHAR, {2} VARCHAR, {3} VARCHAR, {4} DATE, {5} TIME)".format(
    #         table_name,
    #         article_title,
    #         article_text,
    #         article_author,
    #         article_date,
    #         article_time))
    # conn.commit()

    start(conn, table_name)
