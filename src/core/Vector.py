import itertools
import json
import math
import os
from typing import List
import numpy as np
import pathlib

from core import sides, util
from core.config import *


# How much error to tolerate when simplifying the shape
SIMPLIFY_EPSILON = 0 #1.5

# We'll merge vertices closer than this
MERGE_IF_CLOSER_THAN_PX = 2.25

# Opposing sides must be "parallel" within this threshold (in degrees)
SIDE_PARALLEL_THRESHOLD_DEG = 32

# Adjacent sides must be "orthogonal" within this threshold (in degrees)
CORNER_MIN_ANGLE_DEG = 15
CORNER_MAX_ANGLE_DEG = 150
SIDES_ORTHOGONAL_THRESHOLD_DEG = 50

# A side must be at least this long to be considered an edge
EDGE_WIDTH_MIN_RATIO = 0.4

# scale pixel offsets depending on how big the BMPs are
# 1.0 is tuned for around 100 pixels wide
# SCALAR = 9.45
SCALAR = 7.45


def load_and_vectorize(args):
    filename, id, output_path, metadata, photo_space_position, scale_factor, render = args
    v = Vector.from_file(filename, id)
    try:
        return v.process(output_path, metadata, photo_space_position, scale_factor, render)
    except Exception as e:
        print(f"Error while processing id {id} in file {filename}:")
        raise e


class Candidate(object):
    @staticmethod
    def from_vertex(vertices, i, centroid, debug=False):
        i = i % len(vertices)
        v_i = vertices[i]

        if debug:
            print(f"\n\n\n!!!!!!!!!!!!!! {v_i} !!!!!!!!!!!!!!!\n")

        # find the angle from i to the points before it (h), and i to the points after (j)
        vec_offset = 1 if SCALAR < 2 else 2    # we start comparing to this many points away, as really short vectors have noisy angles
        vec_len_for_stdev = round(8 * SCALAR)  # compare this many total points to see the curvature
        vec_len_for_angle = round(3 * SCALAR)  # compare this many total points to see the width of the angle of this corner
        vec_len_for_curve = round(9 * SCALAR)  # wrap around these spokes and see if they form a clean curve or not

        a_ih, _ = util.colinearity(from_point=vertices[i], to_points=util.slice(vertices, i-vec_len_for_angle-vec_offset, i-vec_offset-1))
        a_ij, _ = util.colinearity(from_point=vertices[i], to_points=util.slice(vertices, i+vec_offset+1, i+vec_len_for_angle+vec_offset))

        # extend out along the avg spoke direction
        p_h = (v_i[0] + 10 * math.cos(a_ih), v_i[1] + 10 * math.sin(a_ih))
        p_j = (v_i[0] + 10 * math.cos(a_ij), v_i[1] + 10 * math.sin(a_ij))

        # how wide is the angle between the two legs?
        angle_hij = util.counterclockwise_angle_between_vectors(p_h, v_i, p_j)

        a_ic = util.angle_between(v_i, centroid)
        midangle = util.angle_between(v_i, util.midpoint(p_h, p_j))
        offset_from_center = util.compare_angles(midangle, a_ic)

        is_pointed_toward_center = offset_from_center < angle_hij / 2
        if not is_pointed_toward_center and angle_hij < 90 * math.pi/180:
            # for narrow corners, they might not be pointed directly toward the center but could still be close
            is_pointed_toward_center = abs(offset_from_center) <= (45 * math.pi/180)
        is_valid_angle_width = angle_hij >= CORNER_MIN_ANGLE_DEG * math.pi/180 and angle_hij <= CORNER_MAX_ANGLE_DEG * math.pi/180

        if not is_pointed_toward_center or not is_valid_angle_width:
            if debug:
                print(">>>>>> Skipping; not a valid candidate")
            return None

        # see how straight the spokes are from this point, and what angle they jut out at
        _, stdev_h = util.colinearity(from_point=vertices[i], to_points=util.slice(vertices, i-vec_len_for_stdev-vec_offset, i-vec_offset-1))
        _, stdev_j = util.colinearity(from_point=vertices[i], to_points=util.slice(vertices, i+vec_offset+1, i+vec_len_for_stdev+vec_offset))
        stdev = stdev_h + stdev_j

        points_around = util.slice(vertices, i-vec_len_for_curve, i+vec_len_for_curve)
        curve_score = util.curve_score(points=points_around, debug=debug)

        candidate = Candidate(v=v_i, i=i, centroid=centroid, angular_width=angle_hij, offset_from_center=offset_from_center, midangle=midangle, stdev=stdev, curve_score=curve_score)
        if debug:
            print(f"actually pointed toward center: {offset_from_center < angle_hij / 2}, pointed close enough toward center: {abs(offset_from_center) <= (55 * math.pi/180)}")
            print(f"stdev of spokes: {stdev} = {stdev_h} + {stdev_j}, {vec_len_for_stdev}px out")
            print(f"v: {v_i}, c: {centroid} => {round(a_ic * 180 / math.pi)}°")
            print(f"width: {round(angle_hij * 180 / math.pi)}°, mid-angle ray: {round(midangle * 180 / math.pi)}°")
            print(f"a_ih: {round(a_ih * 180 / math.pi)}°, a_ij: {round(a_ij * 180 / math.pi)}°")
            print(f"a_ic: {round(a_ic * 180 / math.pi)}°, offset: {round(offset_from_center * 180 / math.pi)}°")
            print(f"angle_hij: {round(angle_hij * 180 / math.pi)}°, is_pointed_toward_center: {is_pointed_toward_center}, is valid width: {is_valid_angle_width}")
            print(candidate)

        return candidate

    def __init__(self, v, i, centroid, angular_width=10000, offset_from_center=10000, stdev=10000, midangle=10000, curve_score=10000,):
        self.v = v
        self.i = i
        self.centroid = centroid
        self.angle = angular_width
        self.stdev = stdev
        self.offset_from_center = offset_from_center
        self.midangle = midangle
        self.curve_score = curve_score

    def score(self):
        # lower score = better candidate for a corner
        # we determine "worst" by a mix of:
        # - how far from 90º the join angle is
        # - how far from the center the corner "points": the midangle of the corner typically points quite close to the center of the piece
        # - how non-straight the spokes are

        # how much bigger are we than 90º?
        # If we're less, then we're more likely to be a corner so we don't penalize for below 90º
        angle_error = max(0, self.angle - math.pi/2)
        score = (0.7 * angle_error) + (0.4 * self.offset_from_center) + (11.0 * (self.stdev ** 2)) + (0.8 * self.curve_score)
        return score

    def __repr__(self) -> str:
        return f"Candidate(v={self.v}, i={self.i}, angle={round(self.angle * 180/math.pi, 1)}°, orientation offset={round(self.offset_from_center * 180/math.pi, 1)}°, midangle={round(self.midangle * 180/math.pi, 2)}°, stdev={self.stdev}, score={self.score()})"

    def __eq__(self, __value: object) -> bool:
        return (self.v[0] == __value.v[0]) and (self.v[1] == __value.v[1])

    def __hash__(self) -> int:
        return hash(self.v[0]) + hash(self.v[1])


class Vector(object):
    @staticmethod
    def from_file(filename, id) -> 'Vector':
        # Open image file
        binary_pixels, width, height = util.load_bmp_as_binary_pixels(filename)
        if width > MAX_PIECE_DIMENSIONS[0] or height > MAX_PIECE_DIMENSIONS[1]:
            raise Exception(f"!!!!!!!!!!\nPiece @ {id} {filename} is too large: {width}x{height} - are two pieces touching?")

        v = Vector(pixels=binary_pixels, width=width, height=height, id=id, filename=filename)
        return v

    def __init__(self, pixels, width, height, id, filename=None) -> None:
        self.pixels = pixels
        self.width = width
        self.height = height
        self.dim = float(self.width + self.height) / 2.0
        self.id = id
        self.sides = []
        self.corners = []
        self.filename = filename

    def process(self, output_path=None, metadata={}, photo_space_position=(0, 0), scale_factor=1.0, render=False):
        print(f"> Vectorizing piece {self.id}")
        self.find_border_raster()
        self.vectorize()

        try:
            self.find_four_corners()
            self.extract_four_sides()
            self.enhance_corners()
        except Exception as e:
            self.render()
            print(f"Error while processing id {self.id} in file {self.filename}:")
            raise e

        if render:
            self.render()

        # find the incenter of the piece in the space of the un-scaled original photo
        photo_space_incenter = (photo_space_position[0] + (self.incenter[0] / scale_factor),
                                photo_space_position[1] + (self.incenter[1] / scale_factor))
        metadata["photo_space_incenter"] = photo_space_incenter

        photo_space_centroid = (photo_space_position[0] + (self.centroid[0] / scale_factor),
                                photo_space_position[1] + (self.centroid[1] / scale_factor))
        metadata["photo_space_centroid"] = photo_space_centroid

        if output_path:
            try:
                self.save(output_path, metadata)
            except Exception as e:
                print(f"Error while saving id {self.id} in file {self.filename}:")
                raise e
        else:
            return self

    def save(self, output_path, metadata, only_save_edges=False) -> None:
        if only_save_edges and not any([s.is_edge for s in self.sides]):
            # it's sometimes nice to debug how the border of the puzzle looks
            return

        # We generate an SVG of the piece for debugging
        d = SCALAR / 2.0  # scale the SVG down by this denominator
        colors = ['cc0000', '999900', '00aa99', '3300bb']
        svg = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        svg += f'<svg width="{3 * self.width / d}" height="{3 * self.height / d}" viewBox="-10 -10 {20 + self.width / d} {20 + self.height /d}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        for i, side in enumerate(self.sides):
            stroke_width = 3.0 if side.is_edge else 1.0
            pts = ' '.join([','.join([str(e / d) for e in v]) for v in side.vertices])
            dash = 'stroke-dasharray="6,3"' if side.is_edge else ''
            svg += f'<polyline points="{pts}" style="fill:none; stroke:#{colors[i]}; stroke-width:{stroke_width}" {dash} />'
        # draw in a small circle for each corner (the first and last vertex for each side)
        for corner in self.corners:
            svg += f'<circle cx="{corner[0] / d}" cy="{corner[1] / d}" r="{2.0}" style="fill:none; stroke:#000000aa; stroke-width:0.25" />'
        # if we've enhanced our corners, show the debug output
        if hasattr(self, 'old_corners'):
            for corner in self.old_corners:
                svg += f'<circle cx="{corner[0] / d}" cy="{corner[1] / d}" r="{2.0}" style="fill:none; stroke:#ff3366aa; stroke-width:0.25" />'
            for (slice_a, slice_b) in self.debug_slices:
                pts_a = ' '.join([','.join([str(e / d) for e in v]) for v in slice_a])
                pts_b = ' '.join([','.join([str(e / d) for e in v]) for v in slice_b])
                svg += f'<polyline points="{pts_a}" style="fill:none; stroke:#001100; stroke-width:{1.0}" />'
                svg += f'<polyline points="{pts_b}" style="fill:none; stroke:#000011; stroke-width:{1.0}" />'
            for (trendline_a, trendline_b) in self.debug_trendlines:
                pts_a = ' '.join([','.join([str(e / d) for e in v]) for v in trendline_a])
                pts_b = ' '.join([','.join([str(e / d) for e in v]) for v in trendline_b])
                svg += f'<polyline points="{pts_a}" style="fill:none; stroke:#ffaa00; stroke-width:0.4" />'
                svg += f'<polyline points="{pts_b}" style="fill:none; stroke:#aaff00; stroke-width:0.4" />'
        svg += f'<circle cx="{self.centroid[0] / d}" cy="{self.centroid[1] / d}" r="{1.0}" style="fill:#444444; stroke-width:0" />'
        svg += f'<circle cx="{self.incenter[0] / d}" cy="{self.incenter[1] / d}" r="{50.0 / d}" style="fill:#ff770022; stroke-width:0" />'
        svg += f'<circle cx="{self.incenter[0] / d}" cy="{self.incenter[1] / d}" r="{1.0}" style="fill:#ff7700; stroke-width:0" />'
        svg += '</svg>'
        filename = self.filename.parts[-1].split('.')[0]
        svg_path = pathlib.Path(output_path).joinpath(f"{self.id}_{filename}.svg")
        with open(svg_path, 'w') as f:
            f.write(svg)

        # Then we save off the side data for future processing steps
        for i, side in enumerate(self.sides):
            side_path = pathlib.Path(output_path).joinpath(f"side_{self.id}_{i}.json")
            # convert vertices from np types to native python types
            vertices = [[int(v[0]), int(v[1])] for v in side.vertices]
            metadata['piece_id'] = self.id
            metadata['side_index'] = i
            metadata['vertices'] = vertices
            metadata['piece_center'] = list(side.piece_center)
            metadata['is_edge'] = side.is_edge
            metadata['incenter'] = list(self.incenter)
            with open(side_path, 'w') as f:
                f.write(json.dumps(metadata))

    def find_border_raster(self) -> None:
        # Ensure pixels is a numpy array
        pixels = np.array(self.pixels)

        # Initialize the border array with np.int8 data type
        self.border = np.zeros_like(pixels, dtype=np.int8)

        # Extract slices for the current pixel and its neighbors
        center = pixels[1:-1, 1:-1]
        above = pixels[:-2, 1:-1]
        below = pixels[2:, 1:-1]
        left = pixels[1:-1, :-2]
        right = pixels[1:-1, 2:]

        # Determine border pixels
        border_mask = (center != 0) & ((above == 0) | (below == 0) | (left == 0) | (right == 0))
        self.border[1:-1, 1:-1] = border_mask.astype(np.int8)

    def vectorize(self) -> None:
        """
        We want to "wind" a string around the border
        So we find the top-left most border pixel, then sweep a polyline around the border
        As we go, we capture how much the angle of the polyline changes at each step
        """

        # start at the first border pixel we find
        indices = np.argwhere(self.border == 1)
        sy, sx = tuple(indices[0])

        self.vertices = [(sx, sy)]
        cx, cy = sx, sy
        p_angle = 0

        closed = False
        while not closed:
            neighbors = [
                # Clockwise sweep
                (cx,     cy - 1),  # above
                (cx + 1, cy - 1),  # above right
                (cx + 1, cy),      # right
                (cx + 1, cy + 1),  # below right
                (cx,     cy + 1),  # below
                (cx - 1, cy + 1),  # below left
                (cx - 1, cy),      # left
                (cx - 1, cy - 1),  # above left
            ]
            # pick where to start by looking at the current (absolute) angle, and looking
            # "back over our left shoulder" at the neighbor most in that direction, then sweep CW around the neighbors
            shift = int(round(p_angle * float(len(neighbors))/(2 * math.pi)))  # scale to wrap the full circle over the number of neighbors

            bx, by = cx, cy

            # check each neighbor in order to see if it is also a border
            # once we find one that is a border, add a point to it and continue
            for i in range(0 + shift, 8 + shift):
                nx, ny = neighbors[i % len(neighbors)]
                n = self.border[ny][nx]
                if n == 1:
                    dx, dy = nx - cx, ny - cy
                    abs_angle = math.atan2(dy, dx)
                    rel_angle = abs_angle - p_angle
                    p_angle = abs_angle

                    if rel_angle < 0:
                        rel_angle += 2 * math.pi

                    if self.vertices[-1] != (cx, cy):
                        self.vertices.append((cx, cy))

                    cx, cy = nx, ny
                    if cx == sx and cy == sy:
                        closed = True

                    break

            if bx == cx and by == cy:
                raise Exception(f"Piece @ {self.id} will get us stuck in a loop because the border goes up to the edge of the bitmap. Take a new picture with the piece centered better or make sure the background is brighter white.")

        self.centroid = util.centroid(self.vertices)
        self.incenter = util.incenter(self.vertices) # TODO: remove this, not useful

    def merge_close_points(self, vs, threshold):
        i = -len(vs)
        while i < len(vs):
            i = i % len(vs)
            j = (i + 1) % len(vs)
            if util.distance(vs[i], vs[j]) <= threshold:
                min_v = util.midpoint_along_path(vs, vs[i], vs[j])

                # if the two points are next to each other, don't take the latter one, or else we'll then advance along the path indefinitely if there are more neighboring points
                if min_v == vs[j]:
                    min_v = vs[i]

                vs[i] = min_v
                vs.pop(j)
            else:
                i += 1

    def find_four_corners(self):
        candidates = self.find_corner_candidates()
        candidates = self.merge_nearby_candidates(candidates)
        self.select_best_corners(candidates)

        if len(self.corners) != 4:
            raise Exception(f"Expected 4 corners, found {len(self.corners)} on piece {self.id}")

    def find_corner_candidates(self):
        """
        Finds corners by evaluating the score at each each point
        """
        candidates = []

        # to find a corner, we're going to compute the angle between 3 consecutive points
        # if it is roughly 90º and pointed toward the center, it's a corner
        for i in range(len(self.vertices)):
            debug = self.vertices[i][1] in (2260, 1250)
            candidate = None
            try:
                candidate = Candidate.from_vertex(self.vertices, i, self.centroid, debug=debug)
            except Exception as e:
                print(f"Error while computing curve score for piece {self.id}: {e}")
            curve_score = 0.0

            if not candidate or candidate.score() > 3.0:
                if debug:
                    print(f">>>>>> Skipping; score too high: {candidate.score() if candidate else 0.0}")
                continue
            candidates.append(candidate)

        return candidates

    def merge_nearby_candidates(self, candidates):
        """
        If candidates are within a few indices of each other, merge them by choosing the one with the lowest score
        """
        cs_by_i = sorted(candidates, key=lambda c: c.i)
        j = 0
        while j + 1 < len(cs_by_i):
            c0 = cs_by_i[j]
            c1 = cs_by_i[j + 1]

            # if the two corners are close together, pick the one with the lower score
            # then fast forward past this second candidate
            if c1.i - c0.i <= 2 * SCALAR:
                if c0.score() < c1.score():
                    cs_by_i.remove(c1)
                else:
                    cs_by_i.remove(c0)
            else:
                j += 1
        return cs_by_i

    def select_best_corners(self, candidates):
        """
        We look at the sharpness and the relative position to figure out which candidates make
        the best set of 4 corners

        We first compute a goodness score for each individual corner
        Then we find which set of 4 corners has the best cumulative score, where we'll weigh
        individual corner scores, plus how evenly spread out the 4 corners are (radially)
        """
        # eliminate duplicates
        candidates = list(set(candidates))

        # compute each corner's score, and only consider the n best corners
        candidates = sorted(candidates, key=lambda c: c.score())[:12]

        # for c in candidates:
        #     print(c)

        if len(candidates) < 4:
            raise Exception(f"Expected at least 4 candidates, found {len(candidates)} on piece {self.id}")

        def _score_2_candidates(c0, c1):
            """
            Given a pair of candidate corners, we produce a unitless score for how good they are
            Lower is better
            """
            debug = (c0.v[1] == 6300)

            # first, start with the score of each individual corner
            score = 1.2 * (c0.score() + c1.score())
            if debug:
                print("==========")
                print(c0)
                print(c1)
                print(f"\tInitial score: {score}")

            # we want opposing corners to be roughly 180º radially around the center from each other
            radial_pos0 = util.angle_between(self.centroid, c0.v)
            radial_pos1 = util.angle_between(self.centroid, c1.v)
            radial_delta = abs(radial_pos0 - radial_pos1)
            d180 = abs(radial_delta - math.pi)
            radial_delta_penalty = 0.5 * d180
            score += radial_delta_penalty
            if debug:
                print(f"\tradial_pos0: {round(radial_pos0 * 180 / math.pi)}º, radial_pos1: {round(radial_pos1 * 180 / math.pi)}º, delta: {round(radial_delta * 180 / math.pi)}º, d180: {round(d180 * 180 / math.pi)}º => penalty = {round(radial_delta_penalty, 2)}")
                print(f"\tscore: {score}")

            # the corners should be roughly the same distance from the centroid
            dcenter0 = util.distance(c0.v, self.centroid)
            dcenter1 = util.distance(c1.v, self.centroid)
            dcenter_delta = abs(dcenter0 - dcenter1)/max(dcenter0, dcenter1)
            score += 0.2 * dcenter_delta
            if debug:
                print(f"\tdcenter0: {round(dcenter0)}, dcenter1: {round(dcenter1)}, delta: {round(dcenter_delta, 2)} => penalty = {round(0.1 * dcenter_delta, 2)}")
                print(f"\tscore: {score}")

            # we also want them opening up toward each other
            # (the rays that shoot out should be about 180 degrees apart)
            orientation_delta = abs(c0.midangle - c1.midangle)
            d180_deg = abs(orientation_delta - math.pi) * 180/math.pi
            orientation_penalty = 0.005 * (d180_deg ** 1.0)
            score += orientation_penalty
            if debug:
                print(f"\torientation_delta: {round(orientation_delta * 180 / math.pi)}º, d180: {round(d180_deg)}º => penalty = {round(orientation_penalty, 2)}")
                print(f"\tFinal score: {score}\n")

            return (c0, c1, score)

        def _score_4_candidates(pair0, pair1):
            c0, c1, s01 = pair0
            c2, c3, s23 = pair1
            score = s01 + s23

            # sort the angles by order of radial position around the centroid
            cs = sorted([c0, c1, c2, c3], key=lambda c: util.angle_between(self.centroid, c.v))

            ys = [c.v[1] for c in [c0, c1, c2, c3]]
            debug = 27 in ys and 8 in ys and 4420 in ys
            if debug:
                print("==========")
                for c in cs:
                    print(f" - {c.v}")
                print(f"Base Score: {score}")

            # penalize if the corners are not evenly spread out
            # we want the corners to be roughly 90º radially around the center from each other
            angles = [util.angle_between(self.centroid, c.v) for c in cs]

            if debug:
                for i in range(4):
                    print(f" \t [{i}] {round(angles[i] * 180 / math.pi)}° for {cs[i]}")
            delta_angle_01 = util.compare_angles(angles[0], angles[1])
            delta_angle_12 = util.compare_angles(angles[1], angles[2])
            delta_angle_23 = util.compare_angles(angles[2], angles[3])
            delta_angle_30 = util.compare_angles(angles[3], angles[0])
            if debug:
                print(f" \t   Deltas: {round(delta_angle_01 * 180 / math.pi)}°, {round(delta_angle_12 * 180 / math.pi)}°, {round(delta_angle_23 * 180 / math.pi)}°, {round(delta_angle_30 * 180 / math.pi)}°")
            score_01 = 0.3 * abs(delta_angle_01 - math.pi/2)
            score_12 = 0.3 * abs(delta_angle_12 - math.pi/2)
            score_23 = 0.3 * abs(delta_angle_23 - math.pi/2)
            score_30 = 0.3 * abs(delta_angle_30 - math.pi/2)
            if debug:
                print(f" \t   Penalties: {round(score_01, 2)}, {round(score_12, 2)}, {round(score_23, 2)}, {round(score_30, 2)}")
            score += score_01 + score_12 + score_23 + score_30
            if debug:
                print(f"\t Score: {score}")

            min_delta = min([delta_angle_01, delta_angle_12, delta_angle_23, delta_angle_30])
            if min_delta < 10 * math.pi/180:
                score += 1.0 / (min_delta + 0.01)
                if debug:
                    print(f"\t Score after tight min-delta: {score}")

            cs.append(score)
            return cs

        # Generate all pair combos and score them each up as proposed diagonal corners
        all_pairs = list(itertools.combinations(candidates, 2))
        all_pair_scores = sorted([_score_2_candidates(c0, c1) for (c0, c1) in all_pairs], key=lambda r: r[2])

        # sort so we have a list of pairs, lowest (best) score first
        all_pair_scores = sorted(all_pair_scores, key=lambda c: c[2])
        all_pair_scores = all_pair_scores[:30]  # only consider the best n pairs to save on compute

        # compare pairs of pairs to see how well they work
        all_pair_pairs = list(itertools.combinations(all_pair_scores, 2))
        all_pair_pair_scores = sorted([_score_4_candidates(pair0, pair1) for (pair0, pair1) in all_pair_pairs], key=lambda c: c[4])

        selected_candidates = all_pair_pair_scores[0][0:4]
        self.corners = [c.v for c in selected_candidates]
        self.corner_indices = [c.i for c in selected_candidates]

    def extract_four_sides(self) -> None:
        """
        Once we've found the corners, we'll identify which vertices belong to each side
        We do some validation to make sure the geometry of the piece is sensible
        """
        self.sides = []

        # clean up the vertices and determine if any sides are edges
        for i in range(4):
            # yank out all the relevant vertices for this side
            j = (i + 1) % 4
            c_i = self.corner_indices[i]
            c_j = self.corner_indices[j]
            vertices = util.slice(self.vertices, c_i, c_j)

            # do a bit of simplification
            # vertices = util.ramer_douglas_peucker(vertices, epsilon=0.05)  # I turned this off because we lose density of vertices that the corner-enhancing step relies on
            self.merge_close_points(vertices, threshold=MERGE_IF_CLOSER_THAN_PX)

            # make sure to include the true endpoints
            if vertices[0] != self.corners[i]:
                vertices.insert(0, self.corners[i])
            if vertices[-1] != self.corners[j]:
                vertices.append(self.corners[j])

            # is this side an edge?
            # we see how far from a straight line each vertex is
            # cases that should compute to being an edge:
            # - perfectly straight line (=> no cumulative area)
            # - a perfectly straight line, but with a small defect that leads to some jaggedy edges (=> very small area)
            # cases that should compute to not an edge:
            # - a normal looking puzzle piece side with a nub sticking out
            # - a gentle sloping curve (like the shape of a parenthesis)
            # - a gentle squiggle (like a sine wave)
            area = util.normalized_area_between_corners(vertices)
            # is_edge = bool(area < 0.75 * SCALAR)
            is_edge = bool(area < 10)
            side = sides.Side(piece_id=self.id, side_id=None, vertices=vertices, piece_center=self.centroid, is_edge=is_edge)
            self.sides.append(side)

        # we need to find 4 sides
        if len(self.sides) != 4:
            raise Exception(f"{self.id}: Expected 4 sides, found {len(self.sides)} on piece {self.id}")

        # opposite sides should be parallel
        if abs(self.sides[0].angle - self.sides[2].angle) > SIDE_PARALLEL_THRESHOLD_DEG:
            raise Exception(f"{self.id}: Expected sides 0 and 2 to be parallel, but they are not ({self.sides[0].angle - self.sides[2].angle})")

        if abs(self.sides[1].angle - self.sides[3].angle) > SIDE_PARALLEL_THRESHOLD_DEG:
            raise Exception(f"{self.id}: Expected sides 1 and 3 to be parallel, but they are not ({self.sides[1].angle - self.sides[3].angle})")

        # make sure that sides 0 and 1 are roughly at a right angle
        if abs(self.sides[1].angle - self.sides[0].angle - 90 * math.pi/180.0) >  SIDES_ORTHOGONAL_THRESHOLD_DEG:
            raise Exception(f"{self.id}: Expected sides 0 and 1 to be at a right angle, but they are not ({self.sides[1].angle} - {self.sides[0].angle})")

        d02 = util.distance_between_segments(self.sides[0].segment, self.sides[2].segment)
        d13 = util.distance_between_segments(self.sides[0].segment, self.sides[2].segment)
        if d02 > 1.35 * d13 or d13 > 1.35 * d02:
            raise Exception(f"{self.id}: Expected the piece to be roughly square, but the distance between sides is not comparable ({d02} vs {d13})")

        edge_count = sum([s.is_edge for s in self.sides])
        if edge_count > 2:
            raise Exception(f"{self.id}: A piece cannot be a part of more than 2 edges, found {edge_count}")
        elif edge_count == 2:
            if (self.sides[0].is_edge and self.sides[2].is_edge) or (self.sides[1].is_edge and self.sides[3].is_edge):
                raise Exception(f"{self.id}: A piece cannot be a part of two edges that are parallel!")

    def enhance_corners(self):
        """
        Nudges the corners to where a physical corner would actually be at,
        because pieces tend to get bumped and dinged and corners are most susceptible
        to bending
        """
        self.enhanced_corners = []
        self.debug_slices = []
        self.debug_trendlines = []
        self.old_corners = self.corners.copy()
        self.corner_indices = None  # this field is no longer valid nor needed

        # Go through each pair of sides and improve their intersection point
        # we'll walk back a bit from the corner to find the angle of the side
        #
        #  ---------------*  <- corner
        #     ^       ^   |
        #    MAX     MIN  |
        #
        # we don't go all the way up to the corner because the last little bit might be bent
        SLICE_MIN_DIST_FROM_CORNER = int(round(1.5 * SCALAR))
        SLICE_MAX_DIST_FROM_CORNER = int(round(6.0 * SCALAR))
        for i in range(4):
            j = (i - 1) % 4
            side_i = self.sides[i]
            side_j = self.sides[j]
            corner = self.old_corners[i]

            # for side_i, we take the tail end of the side
            side_i_slice = []
            for v in side_i.vertices:
                if util.distance(v, corner) >= SLICE_MIN_DIST_FROM_CORNER and \
                   util.distance(v, corner) <= SLICE_MAX_DIST_FROM_CORNER:
                    side_i_slice.insert(0, v)

            # and for side_j, we take the head end of the side
            side_j_slice = []
            for v in side_j.vertices:
                if util.distance(v, corner) >= SLICE_MIN_DIST_FROM_CORNER and \
                   util.distance(v, corner) <= SLICE_MAX_DIST_FROM_CORNER:
                    side_j_slice.append(v)

            # find the lines that best approximates those points
            angle_i = util.trendline(side_i_slice)
            angle_j = util.trendline(side_j_slice)
            line_i = util.line_from_angle_and_point(angle=angle_i, point=side_i_slice[-1], length=100)
            line_j = util.line_from_angle_and_point(angle=angle_j, point=side_j_slice[-1], length=100)

            # and the intersection of these lines is our new corner
            enhanced_corner = util.intersection(line_i, line_j)
            if not enhanced_corner:
                print(f"Angle i = {angle_i}\nAngle j = {angle_j}")
                print(f"Line i = {line_i}\nLine j = {line_j}")
                raise Exception(f"[Piece {self.id}] Could not find intersection of lines {line_i} and {line_j}")
            self.corners[i] = enhanced_corner

            # save off debug data for visualization
            self.debug_slices.append([side_i_slice, side_j_slice])
            self.debug_trendlines.append([line_i, line_j])

            # finally, we have to inject these new corners into each sides' vertices
            # we don't want to back-track or jump, so we remove nearby vertices
            for i in range(len(side_j.vertices) - 1, 0, -1):
                # chew off vertices from the tail of j that are close to the corner
                if util.distance(side_j.vertices[i], corner) <= SLICE_MIN_DIST_FROM_CORNER:
                    side_j.vertices.pop(i)
                else:
                    break
            while len(side_i.vertices) > 0:
                # chew off vertices from the head of i that are close to the corner
                if util.distance(side_i.vertices[0], corner) <= SLICE_MIN_DIST_FROM_CORNER:
                    side_i.vertices.pop(0)
                else:
                    break
            side_i.vertices.insert(0, enhanced_corner)
            side_j.vertices.append(enhanced_corner)

    def render(self) -> None:
        SIDE_COLORS = [util.RED, util.GREEN, util.PURPLE, util.CYAN]
        CORNER_COLOR = util.YELLOW
        lines = []
        for row in self.pixels:
            line = []
            for pixel in row:
                line.append('# ' if pixel == 1 else '. ')
            lines.append(line)

        i = 0
        for si, side in enumerate(self.sides):
            for (px, py) in side.vertices:
                color = SIDE_COLORS[si % len(SIDE_COLORS)]
                if py >= len(lines) or px >= len(lines[py]):
                    continue
                lines[py][px] = f"{color}{str(i % 10)} {util.WHITE}"

        for (px, py) in self.corners:
            value = lines[py][px].split(' ')[0][-1]
            lines[py][px] = f"{util.BLACK_ON_BLUE}{value} {util.WHITE}"

        lines[self.centroid[1]][self.centroid[0]] = f"{util.BLACK_ON_RED}X {util.WHITE}"
        lines[self.incenter[1]][self.incenter[0]] = f"{util.BLACK_ON_GREEN}. {util.WHITE}"

        print(f' {util.GRAY} ' + 'v ' * self.width + f"{util.WHITE}")
        for i, line in enumerate(lines):
            line = ''.join(line)
            print(f'{util.GRAY}> {util.WHITE}{line}{util.GRAY}<{util.WHITE} {i}')
        print(f' {util.GRAY} ' + '^ ' * self.width + f"{util.WHITE}")
