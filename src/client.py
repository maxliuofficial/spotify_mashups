import contextlib
import typing as ty

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from webdriver_manager.chrome import ChromeDriverManager


def init_spotipy_client(scope: str = "playlist-read-private") -> Spotify:
    """
    Initialize Spotify client with OAuth.
    """
    # Load client environment variables from .env file
    load_dotenv(override=True)

    return Spotify(
        auth_manager=SpotifyOAuth(
            redirect_uri="http://localhost:9090/callback",
            scope=scope,
            cache_path="/Users/maxliu/Projects/spotify_mashups/.cache",
        )
    )


@contextlib.contextmanager
def open_chrome_driver() -> ty.Iterator[webdriver.Chrome]:
    """
    Create a context manager for using a chrome web driver to scrape pages.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        yield driver
    finally:
        driver.quit()
