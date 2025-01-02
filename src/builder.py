from client import init_spotipy_client, open_chrome_driver
from utils import (
    fetch_current_user,
    fetch_current_user_playlists,
    fetch_unique_tracks,
    scrape_track_metadata_beatport,
)


def build_graph():
    client = init_spotipy_client()
    user = fetch_current_user(client)
    playlists = fetch_current_user_playlists(client, owner_only=user, limit=1)
    tracks = fetch_unique_tracks(client, playlists, limit=3)
    with open_chrome_driver() as driver:
        track_metas = scrape_track_metadata_beatport(driver, tracks)
    for track, meta in track_metas.items():
        print(track, meta)


if __name__ == "__main__":
    build_graph()
