import pathlib

import click

from client import init_spotipy_client, open_chrome_driver
from graph import TrackGraph
from utils import (
    fetch_current_user,
    fetch_current_user_playlists,
    fetch_unique_tracks,
    scrape_track_metadata_beatport,
)


@click.command()
@click.option("--output-path", type=pathlib.Path, required=True)
@click.option(
    "--playlist", "-p", multiple=True, help="Names of playlists to process (defaults to all)"
)
@click.option("--num-playlists", "-n", type=int, help="Maximum number of playlists to process")
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
    output_path: pathlib.Path,
    playlist: list[str],
    num_playlists: int | None,
    num_tracks: int | None,
    all_playlists: bool,
    perfect: bool,
    boost: bool,
    scale: bool,
    diag: bool,
    special: bool,
    bpm_range: float,
) -> None:
    """
    Build a graph of track relationships from Spotify playlists.
    """
    client = init_spotipy_client()
    if all_playlists:
        user = None
    else:
        user = fetch_current_user(client)
    playlists = fetch_current_user_playlists(
        client, owner_only=user, names=playlist or None, limit=num_playlists
    )
    print(playlists)
    # TODO: need to batch this for larger requests.
    tracks = fetch_unique_tracks(client, playlists, limit=num_tracks)
    track_metas = scrape_track_metadata_beatport(open_chrome_driver, tracks)
    print("TRACKS")
    for track, meta in track_metas.items():
        print(track, meta)
    # TODO: make this a separate service, and cache / save the metadata.

    graph = TrackGraph.build_graph(
        track_metas,
        perfect=perfect,
        boost=boost,
        scale=scale,
        diag=diag,
        special=special,
        bpm_range=bpm_range,
    )
    print("GRAPH")
    for track, matches in graph.graph.items():
        print(track, matches)
    graph.to_json(output_path)
    graph = TrackGraph.from_json(output_path)


if __name__ == "__main__":
    build()
