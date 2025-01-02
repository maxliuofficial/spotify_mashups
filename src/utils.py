from __future__ import annotations

import dataclasses
import typing as ty

from selenium import webdriver
from selenium.webdriver.common.by import By
from spotipy import Spotify


@dataclasses.dataclass(frozen=True)
class User:
    name: str
    id: str


@dataclasses.dataclass(frozen=True)
class PlaylistInfo:
    name: str
    id: str
    owner: User
    num_tracks: int


@dataclasses.dataclass(frozen=True)
class TrackInfo:
    name: str
    artist: str
    id: str


@dataclasses.dataclass(frozen=True)
class CamelotKey:
    root: int
    suff: ty.Literal["a", "b"]

    def perfect(self) -> list[CamelotKey]:
        return [self._add(-1), self, self._add(1)]

    def boost(self) -> CamelotKey:
        return self._add(2)

    def scale(self) -> CamelotKey:
        return self._switch()

    def diag(self) -> CamelotKey:
        val = -1 if self.suff == "a" else 1
        return self._add(val)._switch()

    def special(self) -> list[CamelotKey]:
        val = 3 if self.suff == "a" else 9
        return [self._add(7), self._add(val)._switch()]

    def _add(self, val: int) -> CamelotKey:
        return dataclasses.replace(self, root=((self.root + val) - 1) % 12 + 1)

    def _switch(self) -> CamelotKey:
        return dataclasses.replace(
            self,
            suff="a" if self.suff == "b" else "b",
        )

    def __repr__(self) -> str:
        return f"{self.root}{self.suff}"


@dataclasses.dataclass(frozen=True)
class TrackMeta:
    bpm: int
    camelot_key: CamelotKey
    key: str  # Just for viz.


def fetch_current_user(client: Spotify) -> User:
    user_json = client.current_user()
    return User(
        name=user_json["display_name"],
        id=user_json["id"],
    )


def fetch_current_user_playlists(
    client: Spotify,
    owner_only: User | None = None,
    names: set[str] | None = None,
    page: int = 50,
    limit: int | None = None,
) -> list[PlaylistInfo]:
    playlists = []
    ii = 0
    while True:
        playlist_jsons = client.current_user_playlists(limit=page, offset=page * ii)
        for playlist_json in playlist_jsons["items"]:
            playlist_name = playlist_json["name"]
            playlist_owner = playlist_json["owner"]

            # Skip filtered playlists.
            if owner_only and playlist_owner["id"] != owner_only.id:
                continue
            if names and playlist_name not in names:
                continue
            playlists.append(
                PlaylistInfo(
                    name=playlist_json["name"],
                    id=playlist_json["id"],
                    owner=User(
                        name=playlist_owner["display_name"],
                        id=playlist_owner["id"],
                    ),
                    num_tracks=playlist_json["tracks"]["total"],
                )
            )

            # Return early if limit reached.
            if limit is not None and len(playlists) >= limit:
                return playlists

        # Stop if no more pages.
        ii += 1
        if playlist_jsons["next"] is None:
            break

    return playlists


def fetch_unique_tracks(
    client: Spotify,
    playlists: list[PlaylistInfo],
    page: int = 50,
    limit: int | None = None,
) -> list[TrackInfo]:
    # TODO: this may need to be done in chunks if number of tracks is high.
    tracks = set()
    for playlist in playlists:
        ii = 0
        while True:
            track_jsons = client.playlist_tracks(playlist.id, limit=page, offset=page * ii)
            for track_json in track_jsons["items"]:
                track = track_json["track"]
                tracks.add(
                    TrackInfo(
                        name=track["name"],
                        # Just use the first artists since we are scraping the song metadata anyways.
                        artist=track["artists"][0]["name"],
                        id=track["id"],
                    )
                )
                if limit is not None and len(tracks) >= limit:
                    return list(tracks)
            ii += 1
            if track_jsons["next"] is None:
                break
    return list(tracks)


BEATPORT_URL = "https://www.beatport.com"
KEY_TO_CAMELOT_KEY = {
    # Major keys (b)
    "A Major": CamelotKey(11, "b"),
    "A# Major": CamelotKey(6, "b"),
    "Bb Major": CamelotKey(6, "b"),
    "B Major": CamelotKey(1, "b"),
    "C Major": CamelotKey(8, "b"),
    "C# Major": CamelotKey(3, "b"),
    "Db Major": CamelotKey(3, "b"),
    "D Major": CamelotKey(10, "b"),
    "D# Major": CamelotKey(5, "b"),
    "Eb Major": CamelotKey(5, "b"),
    "E Major": CamelotKey(12, "b"),
    "F Major": CamelotKey(7, "b"),
    "F# Major": CamelotKey(2, "b"),
    "Gb Major": CamelotKey(2, "b"),
    "G Major": CamelotKey(9, "b"),
    "G# Major": CamelotKey(4, "b"),
    "Ab Major": CamelotKey(4, "b"),
    # Minor keys (a)
    "A Minor": CamelotKey(8, "a"),
    "A# Minor": CamelotKey(3, "a"),
    "Bb Minor": CamelotKey(3, "a"),
    "B Minor": CamelotKey(10, "a"),
    "C Minor": CamelotKey(5, "a"),
    "C# Minor": CamelotKey(12, "a"),
    "Db Minor": CamelotKey(12, "a"),
    "D Minor": CamelotKey(7, "a"),
    "D# Minor": CamelotKey(2, "a"),
    "Eb Minor": CamelotKey(2, "a"),
    "E Minor": CamelotKey(9, "a"),
    "F Minor": CamelotKey(4, "a"),
    "F# Minor": CamelotKey(11, "a"),
    "Gb Minor": CamelotKey(11, "a"),
    "G Minor": CamelotKey(6, "a"),
    "G# Minor": CamelotKey(1, "a"),
    "Ab Minor": CamelotKey(1, "a"),
}


def scrape_track_metadata_beatport(
    driver: webdriver.Chrome, tracks: list[TrackInfo]
) -> dict[TrackInfo, TrackMeta]:
    # TODO: had to use beatport bc spotify api is deprecated >:( need to find something better.
    results = {}
    for track in tracks:
        # Query the Beatport search page.
        search_url = f"{BEATPORT_URL}/search?q={track.name} {track.artist}".replace(" ", "%20")
        driver.get(search_url)

        # Allow time for the page to load.
        # time.sleep(1)

        # Locate the first track row
        track_row = driver.find_element(By.XPATH, "//div[@data-testid='tracks-table-row']")
        # Extract BPM and Key
        bpm_key_element = track_row.find_element(
            By.XPATH, ".//div[contains(@class, 'cell bpm')]/div"
        )
        # Get the text data.
        bpm, key = bpm_key_element.text.strip().split(" - ")

        results[track] = TrackMeta(
            bpm=int(bpm.replace("BPM", "").strip()),
            camelot_key=KEY_TO_CAMELOT_KEY[key],
            key=key,
        )

    return results
