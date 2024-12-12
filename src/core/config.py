"""
Common configuration for the puzzle bot
"""


# dimensions for the puzzle you're solving
PUZZLE_WIDTH = 40
PUZZLE_HEIGHT = 38
PUZZLE_NUM_PIECES = PUZZLE_WIDTH * PUZZLE_HEIGHT
TIGHTEN_RELAX_PX_W = 5.699827119  # positive = add space between pieces, negative = remove space between pieces
TIGHTEN_RELAX_PX_H = 9.121796862


# Paramaters for photo segmentation
SCALE_BMP_TO_WIDTH = None  # scale the BMP to this wide or None to turn off scaling
CROP_TOP_RIGHT_BOTTOM_LEFT = (620, 860, 620, 860)  # crop the BMP by this many pixels on each side
MIN_PIECE_AREA = 400*400
MAX_PIECE_DIMENSIONS = (1420, 1420)  # we use this to catch when two pieces are touching
SEG_THRESH = 145  # raise this to cut tighter into the border


# Robot parameters
APPROX_ROBOT_COUNTS_PER_PIXEL = 10


# Deduplication
DUPLICATE_CENTROID_DELTA_PX = 22.0


# Directory structure for data processing
# Step 1 takes in photos of pieces on the bed and outputs binary BMPs of those photos
PHOTOS_DIR = '0_photos'
PHOTO_BMP_DIR = '1_photo_bmps'

# Step 2 takes in photo BMPs and outputs cleaned up individual pieces as bitmaps
SEGMENT_DIR = '2_segmented'

# Step 3 takes in piece BMPs and outputs SVGs
VECTOR_DIR = '3_vector'

# Step 4 goes through all the vector pieces and deletes duplicates
DEDUPED_DIR = '4_deduped'

# Step 5 takes in SVGs and outputs a graph of connectivity
CONNECTIVITY_DIR = '5_connectivity'

# Step 6 takes in the graph of connectivity and outputs a solution
SOLUTION_DIR = '6_solution'

# Step 7 adjusts the tightness of the solved puzzle: how much breathing room do pieces need to actually click together?
TIGHTNESS_DIR = '7_tightness'
