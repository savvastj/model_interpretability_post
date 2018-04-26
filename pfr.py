import pandas as pd
from pyquery import PyQuery as pq
import requests
from bs4 import BeautifulSoup
import unicodedata


def get_pfr_id_and_data(idx, td, pfr_id_idx):
    """
    Help get the pfr id as you scrape the data.

    Parameters
    ----------
    idx : int
        The index of the td elements we are enumerating when scraping through
        a row.
    td : tag element
        The td element that contains the information/ player id.
    player_id_idx: int
        The index of the td element with the table row (tr) that contains the
        player id. By defualt we assume the second element of the row contains
        the player id.
    """
    if idx == pfr_id_idx:
        # get the element in the list contains the player name
        # and the associated player id
        return td.text_content(), td.attrib.get("data-append-csv")
    else:
        return td.text_content()


def create_pq(url):
    """
    Create PyQuery object used for scraping pro-football-reference.

    Parameters
    ----------
    url : str
        Url used to create PyQuery objbect

    Returns
    -------
    pq_obj : PyQuery objecy
        PyQuery object used for scraping data
    """
    response = requests.get(url)
    html = response.text.replace('<!--', '').replace('-->', '')
    pq_obj = pq(html)
    return pq_obj


def get_table(url, row_css_selector, col_css_selector,
              pfr_id_idx=None):
    """Scrape the data table and return it as a DataFrame."""
    # set things up using pyquery
    pq_obj = create_pq(url)
    rows = pq_obj(row_css_selector)
    headers = pq_obj(col_css_selector)
    # If we don't want to get the player id, just extract the text data
    if pfr_id_idx is None:
        data = [[td.text_content() for td in row.iterchildren()]
                for row in rows if row.attrib == ""]
    # otherwise get the pfr id from index of the element
    else:
        data = [[get_pfr_id_and_data(idx, td, pfr_id_idx)
                 for idx, td in enumerate(row.iterchildren())]
                for row in rows if row.attrib == ""]
    cols = [th.text_content() for th in headers]
    df = pd.DataFrame(data=data, columns=cols)
    return df


def get_pfr_player_ids_and_info(url):
    """
    Scrape the player ids from a pro-football-reference player directory.

    The function returns the the raw text and link scraped from
    pro-football-reference and the cleaned up columns which contain
    the player names, pfr id, position, and years played (from and to).

    I know this function uses bs4 instead of pyquery but too lazy to switch
    atm.

    Parameters
    ----------
    url : str
        Player directory page.

    Returns
    --------
    df : pd.DataFrame
        A DataFrame contaning pfr player ids and additional information.
    """
    html = requests.get(url).text
    soup = BeautifulSoup(html, "lxml")
    players = soup.select("#div_players p")
    data = [[player.find("a").attrs["href"], player.get_text()]
            for player in players]
    df = pd.DataFrame(data, columns=["Link", "Text"])

    # clean up some of the data to be returned
    df["Pfr_ID"] = df.Link.str.extract("/.*/.*/(.*)\.", expand=False)
    df[["Player", "Pos", "Years"]] = df.Text.str.split("( \(.*\) )",
                                                       expand=True)
    df.loc[:, "Pos"] = (df.Pos.str.replace("(\(|\))", "")
                              .str.rstrip()
                              .str.lstrip())

    df[["From", "To"]] = df.Years.str.split("-", expand=True).astype(int)
    # no need to keep years
    reordered_cols = ["Player", "Pfr_ID", "Pos", "From", "To", "Link", "Text"]
    df = df[reordered_cols]
    return df


def get_college_info(url):
    """
    Scrape college information from a player's bio.

    Returns college information from a player's bio inlcuding college name,
    the associated college link, and the player's college stats url. The
    information is returned as a list of tuples, with either the college
    name or 'College Stats' as the first item in each tuple, and a link
    as the second item in the tuple.

    Parameters
    ----------
    url : str
        The player url to scrape data from.

    Returns
    -------
    info_list : list
        A list of tuples containing the college, college link and/or college
        stats link for the player.
    """
    pq_obj = create_pq(url)
    selector = "#meta > div > p:contains(College)"
    info = pq_obj(selector)
    if len(info) > 0:
        # get the text content clean it up and return it
        info_list = [(e.text_content(),  e.attrib.get("href"))
                     for e in info[0].getchildren()[1:]]
        return info_list
    else:  # Python automatically returns None, but prefer to be explicit
        return None


def get_birth_info(url):
    """
    Scrape birthday and location of a player.

    Parameters
    ----------
    url : str
        The player url to scrape data from.

    Returns
    -------
    info_list : list
        A list containing the birthda and location.
    """
    pq_obj = create_pq(url)
    selector = "#meta > div > p:contains(Born)"
    info = pq_obj(selector)
    if len(info) > 0:
        # get the text content clean it up and return it
        info_list = [e.text_content() for e in info[0].getchildren()[1:]]
        info_list = [unicodedata.normalize("NFKD", i) for i in info_list]
        info_list = [i.strip() for i in info_list]
        return info_list
    else:
        return None
