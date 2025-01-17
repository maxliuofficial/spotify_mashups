from __future__ import annotations

import dataclasses
import json
import math
import pathlib
from collections import defaultdict

from utils import CamelotKey, TrackInfo, TrackMeta


@dataclasses.dataclass
class TrackGraph:
    graph: dict[TrackInfo, set[TrackInfo]]

    @classmethod
    def build_graph(
        cls,
        track_metas: dict[TrackInfo, TrackMeta],
        *,
        perfect: bool,
        boost: bool,
        scale: bool,
        diag: bool,
        special: bool,
        bpm_range: float,
    ) -> TrackGraph:
        """
        Build a graph of compatible songs for mixing based on a map of tracks to track meta.
        Configurations include:
        - key compatibility ie perfect, boost, scale, diag, special (see https://dj.studio/blog/camelot-wheel for info).
        - bpm range (as a percentage of song bpm).
        """
        assert any([perfect, boost, scale, diag, special])
        assert 0.0 <= bpm_range <= 1.0
        graph: dict[TrackInfo, set[TrackInfo]] = defaultdict(set)
        tail = 0
        window: dict[CamelotKey, set[TrackInfo]] = defaultdict(set)
        sorted_by_bpm = sorted(track_metas.items(), key=lambda item: item[1].bpm)
        for track, meta in sorted_by_bpm:
            # Pop tracks out of the window that are outside the bpm range.
            bpm_diff = math.ceil(meta.bpm * bpm_range)
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
        return cls(graph)

    def to_json(self, path: pathlib.Path) -> None:
        # TODO: add versioning, etc as needed.
        as_jsonable = [
            (dataclasses.asdict(track), [dataclasses.asdict(nbr) for nbr in nbrs])
            for track, nbrs in self.graph.items()
        ]

        path.mkdir(parents=True, exist_ok=True)
        with (path / "graph.json").open("w") as handle:
            json.dump(as_jsonable, handle)

    @classmethod
    def from_json(cls, path: pathlib.Path) -> TrackGraph:
        with (path / "graph.json").open() as handle:
            raw: list[tuple[dict, list[dict]]] = json.load(handle)

        graph = {}
        for track_dict, nbrs in raw:
            track = TrackInfo(**track_dict)
            graph[track] = {TrackInfo(**nbr) for nbr in nbrs}
        return cls(graph)
