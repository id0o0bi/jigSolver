import os
import json
import numpy as np

from core import sides

class Piece(object):
    @staticmethod
    def load_all(directory, resample=False):
        pieces = {}
        for f in os.listdir(directory):
            if not f.startswith("side_"):
                continue
            id = int(f.split("_")[1])
            piece = Piece.load(directory, id=id, resample=resample)
            pieces[piece.id] = piece
        return pieces

    @classmethod
    def load(cls, directory, id, resample):
        sides_list = []
        for side_index in range(4):
            path = os.path.join(directory, f"side_{id}_{side_index}.json")
            with open(path, "r") as f:
                data = json.load(f)
            side = sides.Side(piece_id=id, side_id=side_index, vertices=np.array(data['vertices']), piece_center=data['piece_center'], is_edge=data['is_edge'], resample=resample)
            sides_list.append(side)
        piece = cls(id=id, is_edge=False, sides=sides_list)
        return piece

    def to_dict(self) -> dict:
        fits = [[], [], [], []]
        for i in range(4):
            for (other_piece_id, other_side_index, error) in self.fits[i]:
                fits[i].append([other_piece_id, other_side_index, round(error * 1000)])

        return fits

    def __init__(self, id, is_edge, sides) -> None:
        self.id = id
        self.sides = sides
        self.fits = [
            [], [], [], []
        ]

    def __repr__(self) -> str:
        return f"(id={self.id}, fits0={self.fits[0]}, fits1={self.fits[1]}, fits2={self.fits[2]}, fits3={self.fits[3]})"
