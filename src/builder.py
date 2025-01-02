import math
from collections import defaultdict

import click

from client import init_spotipy_client, open_chrome_driver
from utils import (
    CamelotKey,
    TrackInfo,
    TrackMeta,
    fetch_current_user,
    fetch_current_user_playlists,
    fetch_unique_tracks,
    scrape_track_metadata_beatport,
)


@click.command()
@click.option("--playlist-names", "-n", multiple=True, help="Names of playlists to process")
@click.option("--num-playlists", "-p", type=int, help="Maximum number of playlists to process")
@click.option("--num-tracks", "-t", type=int, help="Maximum number of tracks to process")
@click.option(
    "--all-playlists", "-a", is_flag=True, default=False, help="Process playlists not owned by user"
)
@click.option("--perfect", is_flag=True, default=False)
@click.option("--boost", is_flag=True, default=False)
@click.option("--scale", is_flag=True, default=False)
@click.option("--diag", is_flag=True, default=False)
@click.option("--special", is_flag=True, default=False)
@click.option("--bpm-range", type=float, default=0.1)
def build(
    playlist_names: list[str],
    num_playlists: int | None,
    num_tracks: int | None,
    all_playlists: bool,
    perfect: bool,
    boost: bool,
    scale: bool,
    diag: bool,
    special: bool,
    bpm_range: float,
):
    """Build a graph of track relationships from Spotify playlists."""
    client = init_spotipy_client()
    if all_playlists:
        user = None
    else:
        user = fetch_current_user(client)
    playlists = fetch_current_user_playlists(
        client, owner_only=user, names=playlist_names or None, limit=num_playlists
    )
    print(playlists)
    # TODO: need to batch this for larger requests.
    tracks = fetch_unique_tracks(client, playlists, limit=num_tracks)
    with open_chrome_driver() as driver:
        track_metas = scrape_track_metadata_beatport(driver, tracks)
    print("TRACKS")
    for track, meta in track_metas.items():
        print(track, meta)
    # TODO: make this a separate service, and cache / save the metadata.
    graph = build_graph(
        track_metas,
        perfect=perfect,
        boost=boost,
        scale=scale,
        diag=diag,
        special=special,
        bpm_range=bpm_range,
    )
    print("GRAPH")
    for track, matches in graph.items():
        print(track, matches)


def build_graph(
    track_metas: dict[TrackInfo, TrackMeta],
    *,
    perfect: bool,
    boost: bool,
    scale: bool,
    diag: bool,
    special: bool,
    bpm_range: float,
):
    assert any([perfect, boost, scale, diag, special])
    assert 0.0 <= bpm_range <= 1.0
    graph: dict[TrackInfo, set[TrackInfo]] = defaultdict(set)
    tail = 0
    window: dict[CamelotKey, set[TrackInfo]] = defaultdict(set)
    sorted_by_bpm = sorted(track_metas.items(), key=lambda item: item[1].bpm)
    for track, meta in sorted_by_bpm:
        # Pop tracks out of the window that are outside the bpm range.
        bpm_diff = math.ceil(meta.bpm * bpm_range)
        print(meta.bpm, bpm_diff)
        while (tail_track := sorted_by_bpm[tail])[1].bpm < meta.bpm - bpm_diff:
            window[tail_track[1].camelot_key].remove(tail_track[0])
            tail += 1
        # Get possible key pairings.
        pairings = []
        if perfect:
            pairings.extend(meta.camelot_key.perfect())
        if boost:
            pairings.append(meta.camelot_key.boost())
        if scale:
            pairings.append(meta.camelot_key.scale())
        if diag:
            pairings.append(meta.camelot_key.diag())
        if special:
            pairings.extend(meta.camelot_key.special())
        # Add pairings to graph.
        for key in pairings:
            graph[track].update(window[key])
        # Add the current track to the sliding window.
        window[meta.camelot_key].add(track)
    return graph


if __name__ == "__main__":
    build()
