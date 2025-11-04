import random
import pygame
from os import listdir
from os.path import isfile, join
from settings import PLAYER_VEL, FPS, BLOCK_SIZE, WIDTH, HEIGHT

# Utility: flip sprite surfaces horizontally (not used for cube but kept for assets)
def flip(sprites):
	"""Return horizontally flipped copies of sprite Surfaces."""
	return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, width, height, direction=False):
	"""
	Loads and slices sprite sheets. This should only be called when a pygame
	display surface exists (convert_alpha requires an initialized display).
	"""
	path = join("Assets", dir1, dir2)
	images = [f for f in listdir(path) if isfile(join(path, f))]

	all_sprites = {}

	for image in images:
		# Load image normally; convert_alpha will be applied only when display exists
		img = pygame.image.load(join(path, image))
		# if display is initialized we can safely convert_alpha
		try:
			if pygame.display.get_surface() is not None:
				img = img.convert_alpha()
		except Exception:
			# fallback: keep raw Surface
			pass
		sprites = []
		for i in range(img.get_width() // width):
			surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
			rect = pygame.Rect(i * width, 0, width, height)
			surface.blit(img, (0, 0), rect)
			sprites.append(pygame.transform.scale2x(surface))

		if direction:
			key_base = image.replace(".png", "")
			all_sprites[key_base + "_right"] = sprites
			all_sprites[key_base + "_left"] = flip(sprites)
		else:
			all_sprites[image.replace(".png", "")] = sprites

	return all_sprites


def get_block(size):
	"""
	Return a block Surface taken from the terrain tilesheet.
	This is used to draw ground/platform visuals.
	"""
	path = join("Assets", "Terrain", "3aa9ff21fc29b32.png")
	image = pygame.image.load(path)
	try:
		if pygame.display.get_surface() is not None:
			image = image.convert_alpha()
	except Exception:
		pass
	surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
	rect = pygame.Rect(96, 0, size, size)
	surface.blit(image, (0, 0), rect)
	return pygame.transform.scale2x(surface)


# Player class (originally animated; kept sprites support)
class Player(pygame.sprite.Sprite):
	"""
	Represents the player character.
	- This project previously used animated sprites; the class maintains sprite support.
	- x_vel/y_vel track velocity. jump_count allows double-jump logic.
	"""
	# Dash parameters (px/sec, seconds)
	DASH_SPEED = 900.0       # pixels per second during dash
	DASH_DURATION = 0.18     # seconds dash lasts
	DASH_COOLDOWN = 1.5      # seconds between dashes

	# Stomp parameters
	STOMP_GRAVITY_MULTIPLIER = 10  # gravity multiplier during stomp
	STOMP_DURATION = 3.0             # seconds stomp lasts
	STOMP_COOLDOWN = 3.0             # seconds between stomps

	COLOR = (255, 0, 0)
	GRAVITY = 1
	# don't load sprites at import-time (display may not be ready)
	SPRITES = {}
	ANIMATION_DELAY = 3

	# Add ledge-hold defaults
	HOLD_MAX = 10.0  # seconds
	def __init__(self, x, y, width, height):
		super().__init__()
		# rect represents position and size in world coordinates
		self.rect = pygame.Rect(x, y, width, height)
		self.x_vel = 0
		self.y_vel = 0
		self.mask = None
		self.direction = "left"
		self.animation_count = 0
		self.fall_count = 0    # used to calculate falling acceleration
		self.jump_count = 0    # 0=grounded, 1=jump used, 2=double jump used
		self.hit = False
		self.hit_count = 0

		# ledge hold state
		self.holding = False
		self.hold_time = 0.0
		self.hold_block = None
		self.hold_side = None  # 'left' or 'right'

		# short cooldown to prevent immediate re-grab when releasing a hold or jumping from one
		self.hold_regrab_cooldown = 0.0

		# dash state
		self.dash_timer = 0.0
		self.dash_cooldown_timer = self.DASH_COOLDOWN
		self.dashing = False
		self.dash_dir = 0
		self.dash_speed = self.DASH_SPEED

		# stomp state
		self.stomp_timer = 0.0
		self.stomp_cooldown_timer = self.STOMP_COOLDOWN
		self.stomping = False

		# Try to load sprites now that main likely initialized the display.
		self.ensure_sprites_loaded()

		# default sprite fallback (simple rect if sheets missing)
		try:
			self.sprite = self.SPRITES["idle_left"][0]
			self.update()
		except Exception:
			self.sprite = pygame.Surface((width, height), pygame.SRCALPHA)
			pygame.draw.rect(self.sprite, self.COLOR, (0,0,width,height))
			self.update()

	def jump(self):
		"""Apply an instantaneous upward velocity for jumping."""
		self.y_vel = -self.GRAVITY * 8
		self.animation_count = 0
		self.jump_count += 1
		if self.jump_count == 1:
			# reset fall counter on first jump
			self.fall_count = 0

	def move(self, dx, dy):
		"""Move rect by dx, dy (no collision handling here)."""
		self.rect.x += dx
		self.rect.y += dy

	def make_hit(self):
		"""Mark player as hit (for visuals/logic elsewhere)."""
		self.hit = True

	def move_left(self, vel):
		"""Set horizontal velocity to move left."""
		self.x_vel = -vel
		if self.direction != "left":
			self.direction = "left"
			self.animation_count = 0

	def move_right(self, vel):
		"""Set horizontal velocity to move right."""
		self.x_vel = vel
		if self.direction != "right":
			self.direction = "right"
			self.animation_count = 0

	def dash(self):
		"""Start a dash in the current facing direction if off cooldown."""
		if self.dash_cooldown_timer >= self.DASH_COOLDOWN and not self.holding:
			self.dashing = True
			self.dash_timer = self.DASH_DURATION
			self.dash_cooldown_timer = 0.0
			self.dash_dir = -1 if self.direction == "left" else 1
			# stop existing horizontal velocity to let dash control movement
			self.x_vel = 0
			return True
		return False

	def stomp(self):
		"""Start a stomp if off cooldown and not holding or dashing."""
		if self.stomp_cooldown_timer >= self.STOMP_COOLDOWN and not self.holding and not self.dashing:
			self.stomping = True
			self.stomp_timer = self.STOMP_DURATION
			self.stomp_cooldown_timer = 0.0
			return True
		return False

	def loop(self, fps, dt):
		"""
		Per-frame update:
		- dt: seconds elapsed this frame (fixed timestep recommended)
		- fps: frames-per-second used by other frame-dependent calculations
		"""
		# decrement regrab cooldown and advance dash cooldown using dt
		if getattr(self, "hold_regrab_cooldown", 0.0) > 0.0:
			self.hold_regrab_cooldown = max(0.0, self.hold_regrab_cooldown - dt)

		self.dash_cooldown_timer = min(self.DASH_COOLDOWN, self.dash_cooldown_timer + dt)
		self.stomp_cooldown_timer = min(self.STOMP_COOLDOWN, self.stomp_cooldown_timer + dt)

		# If holding a ledge, freeze motion and don't apply gravity/movement.
		if self.holding:
			self.x_vel = 0
			self.y_vel = 0
			if self.hit:
				self.hit_count += 1
			if self.hit_count > fps * 2:
				self.hit = False
				self.hit_count = 0
			self.update_sprite()
			return

		# If currently dashing, move by dash_speed * dt and ignore gravity for the dash duration.
		if self.dashing:
			# move horizontally by dash (convert px/sec to px this frame)
			dx = int(self.dash_dir * self.dash_speed * dt)
			if dx != 0:
				self.move(dx, 0)
			self.dash_timer = max(0.0, self.dash_timer - dt)
			if self.dash_timer <= 0.0:
				self.dashing = False
				self.x_vel = 0
			self.update_sprite()
			return

		# If currently stomping, apply increased gravity for the stomp duration.
		if self.stomping:
			# apply increased gravity
			self.y_vel += min(1,self.GRAVITY * self.STOMP_GRAVITY_MULTIPLIER)
			self.move(self.x_vel, self.y_vel)
			self.stomp_timer = max(0.0, self.stomp_timer - dt)
			if self.stomp_timer <= 0.0:
				self.stomping = False
			if self.hit:
				self.hit_count += 1
			if self.hit_count > fps * 2:
				self.hit = False
				self.hit_count = 0
			self.fall_count += 1
			self.update_sprite()
			return

		# Default behavior when not holding, dashing, or stomping (keeps original frame-based gravity)
		self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
		self.move(self.x_vel, self.y_vel)

		if self.hit:
			self.hit_count += 1
		if self.hit_count > fps * 2:
			self.hit = False
			self.hit_count = 0

		self.fall_count += 1
		self.update_sprite()

	def landed(self):
		"""Called when player lands on a surface: reset vertical state."""
		self.fall_count = 0
		self.y_vel = 0
		self.jump_count = 0

	def hit_head(self):
		"""Called when player hits their head on a ceiling: invert y velocity slightly."""
		self.count = 0
		self.y_vel *= -1

	def update_sprite(self):
		"""
		Select and update the sprite frame based on state (idle/run/jump/fall/hit).
		If you converted to a non-animated cube, you can simplify this method.
		"""
		sprite_sheet = "idle"
		if self.hit:
			sprite_sheet = "hit"
		elif self.y_vel < 0:
			if self.jump_count == 1:
				sprite_sheet = "jump"
			elif self.jump_count == 2:
				sprite_sheet = "double_jump"
		elif self.y_vel > self.GRAVITY * 2:
			sprite_sheet = "fall"
		elif self.x_vel != 0:
			sprite_sheet = "run"

		sprite_sheet_name = sprite_sheet + "_" + self.direction
		try:
			if self.SPRITES:
				sprites = self.SPRITES[sprite_sheet_name]
				sprite_index = (self.animation_count // self.ANIMATION_DELAY) % len(sprites)
				self.sprite = sprites[sprite_index]
		except Exception:
			# fallback: keep existing sprite
			pass
		self.animation_count += 1
		self.update()

	def update(self):
		"""Recompute rect and collision mask from the current sprite Surface."""
		self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
		self.mask = pygame.mask.from_surface(self.sprite)

	def draw(self, win, offset_x):
		"""Blit the player sprite to the window, offset by camera offset_x."""
		win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))

	def start_hold(self, block, side):
		"""Begin holding onto the given block on the given side ('left' or 'right')."""
		self.holding = True
		self.hold_time = 0.0
		self.hold_block = block
		self.hold_side = side
		# freeze vertical velocity and horizontal movement
		self.x_vel = 0
		self.y_vel = 0
		# snap player next to ledge in world coordinates (horizontal first)
		if side == "right":
			# block is to the right of player, snap player to block's left side
			self.rect.x = block.rect.left - self.rect.width - 1
		else:
			# block is to the left of player, snap player to block's right side
			self.rect.x = block.rect.right + 1

		# ensure sprite/rect are up-to-date, then snap vertically flush to the block top
		try:
			self.update()  # ensure rect size matches sprite
		except Exception:
			pass
		# place player's bottom exactly at block top (minus tiny epsilon to avoid penetration)
		self.rect.bottom = block.rect.top
		# reset fall counter
		self.fall_count = 0

	def end_hold(self):
		"""Release ledge hold and resume normal physics."""
		self.holding = False
		self.hold_time = 0.0
		self.hold_block = None
		self.hold_side = None
		# start a short cooldown to avoid immediate re-grab when SPACE still held
		self.hold_regrab_cooldown = 0.25
		# do not alter velocities here beyond letting gravity take effect next frame

	@classmethod
	def ensure_sprites_loaded(cls):
		"""Attempt to load sprite sheets if they haven't been loaded and a display exists."""
		if cls.SPRITES:
			return
		# only attempt if a display surface exists
		try:
			if pygame.display.get_surface() is None:
				return
		except Exception:
			return

		try:
			cls.SPRITES = load_sprite_sheets("MainCharacter", "", 32, 32, True)
		except Exception:
			# if loading fails (missing assets or other error) leave SPRITES empty
			cls.SPRITES = {}


# Generic object base class used for blocks, fire traps, etc.
class Object(pygame.sprite.Sprite):
	def __init__(self, x, y, width, height, name=None):
		super().__init__()
		# Objects store their own surface in .image and position in .rect
		self.rect = pygame.Rect(x, y, width, height)
		self.image = pygame.Surface((width, height), pygame.SRCALPHA)
		self.width = width
		self.height = height
		self.name = name

	def draw(self, win, offset_x):
		"""Draw object image at world position minus camera offset."""
		# allow invisible collision-only objects by setting obj.invisible = True
		if getattr(self, "invisible", False):
			return
		win.blit(self.image, (self.rect.x - offset_x, self.rect.y))


class Block(Object):
	"""
	Terrain block. Uses get_block to get a consistent tile graphic.
	.mask is created for pixel-perfect collision checks.
	"""
	def __init__(self, x, y, size):
		super().__init__(x, y, size, size)
		block = get_block(size)
		self.image.blit(block, (0, 0))
		self.mask = pygame.mask.from_surface(self.image)


def handle_vertical_collision(player, objects, dy):
	collided_objects = []
	for obj in objects:
		if pygame.sprite.collide_mask(player, obj):
			if dy > 0:
				player.rect.bottom = obj.rect.top
				player.landed()
			elif dy < 0:
				player.rect.top = obj.rect.bottom
				player.hit_head()
			collided_objects.append(obj)
	return collided_objects


def collide(player, objects, dx):
	"""
	Check for horizontal collisions by moving player horizontally by dx,
	checking masks, then moving back.
	Returns the first collided object or None.
	"""
	player.move(dx, 0)
	player.update()
	collided_object = None
	for obj in objects:
		if pygame.sprite.collide_mask(player, obj):
			collided_object = obj
			break

	player.move(-dx, 0)
	player.update()
	return collided_object


# Handle keyboard input and prevent movement into colliding objects
def handle_move(player, objects):
	keys = pygame.key.get_pressed()

	player.x_vel = 0
	# pre-check collisions a bit further to avoid tunneling on fast movement
	collide_left = collide(player, objects, -PLAYER_VEL * 2)
	collide_right = collide(player, objects, PLAYER_VEL * 2)

	# Movement now uses A/D
	if keys[pygame.K_a] and not collide_left:
		player.move_left(PLAYER_VEL)
	if keys[pygame.K_d] and not collide_right:
		player.move_right(PLAYER_VEL)

	vertical_collide = handle_vertical_collision(player, objects, player.y_vel)
	to_check = [collide_left, collide_right, *vertical_collide]


# Keep ground blocks generated in a band around the camera so ground appears infinite
def update_ground(objects, block_size, offset_x, ground_y):
	"""
	Ensure ground blocks cover a horizontal band around the camera.
	- Keeps blocks within [start_x, end_x] and removes ones outside.
	- Adds missing blocks so the ground appears infinite as the player moves.
	"""
	margin = WIDTH  # extra ground to keep left/right of screen
	start_x = (int((offset_x - margin) // block_size)) * block_size
	end_x = (int((offset_x + WIDTH + margin) // block_size)) * block_size

	# compute which x positions we need to have ground blocks at
	needed = set(range(start_x, end_x + 1, block_size))

	# find existing ground block x positions
	existing = set(obj.rect.x for obj in objects if isinstance(obj, Block) and obj.rect.y == ground_y)

	# remove ground blocks that are outside needed range
	for obj in objects[:]:
		if isinstance(obj, Block) and obj.rect.y == ground_y and obj.rect.x not in needed:
			objects.remove(obj)

	# add missing ground blocks
	for x in sorted(needed - existing):
		objects.append(Block(x, ground_y, block_size))


# Replace the dummy ledge handler with a real implementation
def handle_ledge_grab(player, objects, dt, block_size):
	"""
	Manage ledge grabbing/holding using right mouse button as the grab key.
	"""
	# use right mouse button (index 2) for grabbing
	right_pressed = pygame.mouse.get_pressed()[2]

	# If already holding, maintain or release
	if player.holding:
		# Ensure block still exists
		if player.hold_block not in objects:
			player.end_hold()
			return

		# Release if right button released
		if not right_pressed:
			player.end_hold()
			return

		# Allow jump while holding (release + jump)
		keys = pygame.key.get_pressed()
		if keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]:
			player.end_hold()
			player.jump()
			return

		# keep player snapped to the held block (both X and Y) to avoid drifting/gaps
		b = player.hold_block
		if player.hold_side == "right":
			player.rect.x = b.rect.left - player.rect.width - 1
		else:
			player.rect.x = b.rect.right + 1
		# force the bottom to block top to eliminate small vertical gaps
		player.rect.bottom = b.rect.top
		player.x_vel = 0
		player.y_vel = 0

		# accumulate hold time and auto-release if exceeded
		player.hold_time += dt
		if player.hold_time >= player.HOLD_MAX:
			player.end_hold()
			return

	# Not holding: must hold right mouse to attempt grab
	if not right_pressed:
		return

	# short cooldown to prevent immediate re-grab
	if getattr(player, "hold_regrab_cooldown", 0.0) > 0.0:
		return

	# Must be airborne and falling (no grab while grounded or moving up)
	if getattr(player, "jump_count", 0) == 0 or player.y_vel <= 0:
		return

	# Don't allow while stomping/dashing
	if getattr(player, "stomping", False) or getattr(player, "dashing", False):
		return

	# Tolerances
	horiz_thresh = max(8, block_size // 6)   # horizontal tolerance in px
	vert_tolerance = block_size // 3  # vertical tolerance in px

	facing = getattr(player, "direction", "right")

	# try to find a nearby block edge to grab
	for obj in objects:
		if not isinstance(obj, Block):
			continue
		b = obj
		# right side of player near left side of block
		if abs(player.rect.right - b.rect.left) <= horiz_thresh:
			# check if player is falling past the ledge (bottom at or below block top, but not too far)
			if player.rect.bottom >= b.rect.top and player.rect.bottom <= b.rect.top + vert_tolerance:
				player.start_hold(b, "right")
				return
		# left side of player near right side of block
		if abs(player.rect.left - b.rect.right) <= horiz_thresh:
			if player.rect.bottom >= b.rect.top and player.rect.bottom <= b.rect.top + vert_tolerance:
				player.start_hold(b, "left")
				return


# Add helper methods to Player: start_hold and end_hold
# Insert these methods into the Player class definition if not present:
def _player_start_hold(self, block, side):
    """Begin holding onto a side block (side == 'left'|'right')."""
    self.holding = True
    self.hold_block = block
    self.hold_side = side
    self.hold_time = 0.0
    # snap immediately
    if side == "right":
        self.rect.right = block.rect.left - 1
    else:
        self.rect.left = block.rect.right + 1
    self.rect.bottom = block.rect.top
    self.x_vel = 0
    self.y_vel = 0
    # small cooldown to avoid immediate regrab after release
    self.hold_regrab_cooldown = 0.0

def _player_end_hold(self):
    """End any current hold; apply a tiny regrab cooldown to avoid flicker."""
    self.holding = False
    self.hold_block = None
    self.hold_side = None
    self.hold_time = 0.0
    # slightly block immediate re-grab
    self.hold_regrab_cooldown = 0.15

# Bind helpers onto Player class at runtime if class defined
try:
    Player.start_hold
except Exception:
    Player.start_hold = _player_start_hold
    Player.end_hold = _player_end_hold


def generate_cubes(x_min, x_max, num_cubes, block_size, occupied, ground_y, player_rect, max_vertical_gap=220, min_gap=None):
	"""
	Generate clusters of airborne platforms and single cubes between x_min and x_max.
	Guarantees each placed platform/cube is reachable by at least a double-jump from ground,
	an existing platform, or from the player (player_rect).
	- player_rect: pygame.Rect for the player; treated as a temporary support source.
	"""
	if min_gap is None:
		min_gap = block_size // 2

	placed = []
	placed_set = set()  # track (x,y) of blocks placed in this call
	attempts = 0
	max_attempts = num_cubes * 80

	# horizontal reach used to ensure platforms are accessible from each other (tweak to taste)
	horizontal_reach = block_size * 4

	# helper to check for support either in existing occupied, in placed_set, or the player
	def has_support_near(xp, yp):
		# any support (sx,sy) below yp within vertical and horizontal tolerances
		# include player as support
		if player_rect is not None:
			sx = player_rect.centerx
			sy = player_rect.bottom
			if sy > yp and (sy - yp) <= max_vertical_gap and abs(sx - xp) <= horizontal_reach:
				return True
		for (sx, sy) in (set(occupied) | placed_set):
			if sy <= yp:
				continue
			if sy - yp <= max_vertical_gap and abs(sx - xp) <= horizontal_reach:
				return True
		return False

	# find nearest support (existing occupied) for xp, yp
	def find_nearest_support(xp, yp):
		best = None
		best_dist = None
		# prefer existing world occupied blocks
		for (sx, sy) in occupied:
			if sy <= yp:
				continue
			vert = sy - yp
			horiz = abs(sx - xp)
			if vert <= max_vertical_gap and horiz <= horizontal_reach:
				dist = vert + horiz / (block_size or 1)
				if best_dist is None or dist < best_dist:
					best = (sx, sy)
					best_dist = dist
		# also consider player as a support candidate if applicable
		if best is None and player_rect is not None:
			sx = player_rect.centerx
			sy = player_rect.bottom
			if sy > yp and (sy - yp) <= max_vertical_gap and abs(sx - xp) <= horizontal_reach:
				best = (sx, sy)
		return best

	# Build a short helper column from nearest support downward or from ground upward so that yp gets a support within max_vertical_gap.
	def build_helper_column_towards_support(xp, yp):
		helpers = []
		support = find_nearest_support(xp, yp)
		if support:
			(sx, sy) = support
			y = sy - block_size
			count = 0
			max_helpers = max_vertical_gap // block_size + 2
			while y > yp and (xp, y) not in occupied and (xp, y) not in placed_set and count < max_helpers:
				placed_set.add((xp, y))
				helpers.append(Block(xp, y, block_size))
				count += 1
				y -= block_size
			if y <= yp:
				return helpers
			# rollback
			for h in helpers:
				placed_set.discard((h.rect.x, h.rect.y))
			helpers = []

		# fallback: build from ground upward
		y = ground_y - block_size
		count = 0
		max_helpers = max_vertical_gap // block_size + 2
		while y > yp and (xp, y) not in occupied and (xp, y) not in placed_set and count < max_helpers:
			placed_set.add((xp, y))
			helpers.append(Block(xp, y, block_size))
			count += 1
			y -= block_size
		if y > yp:
			for h in helpers:
				placed_set.discard((h.rect.x, h.rect.y))
			return []
		return helpers

	# allowable y range: within vertical reach of a double jump from ground
	min_y = max(0, ground_y - max_vertical_gap)
	max_y = ground_y - block_size

	# candidate heights across the reachable band (more varied - not only fixed layers)
	candidate_heights = list(range(max_y, min_y - 1, -block_size))
	random.shuffle(candidate_heights)

	# horizontal grid candidates
	step = block_size
	xs = list(range(x_min, x_max - block_size + 1, step))
	random.shuffle(xs)

	while len(placed) < num_cubes and attempts < max_attempts and xs:
		attempts += 1
		x0 = xs.pop()
		x0 = (x0 // block_size) * block_size

		# pick a random height from candidates for this placement (varies heights)
		if not candidate_heights:
			continue
		y = random.choice(candidate_heights)

		# skip exact overlap
		if any((x0 == ox and abs(y - oy) < 1) for (ox, oy) in occupied) or (x0, y) in placed_set:
			continue

		# choose platform length (favor multi-block sometimes)
		length = random.choice([1,1,2,2,3,4])

		if x0 + length * block_size > x_max:
			continue

		positions = [(x0 + i * block_size, y) for i in range(length)]
		# avoid overlaps with occupied or already placed in this batch
		if any(pos in occupied or pos in placed_set for pos in positions):
			continue

		# spacing check at same y
		if any(oy == y and any(abs(ox - px) < (block_size + min_gap) for (px, _) in positions) for (ox, oy) in (set(occupied) | placed_set)):
			continue

		# Check accessibility: at least one tile must have support within double-jump distance from ground/platform/player
		if any(has_support_near(px, y) for (px, _) in positions):
			support_exists = True
		else:
			support_exists = False

		helpers_added = []
		if not support_exists:
			# attempt to build a helper column below middle block connecting to nearest support (including player)
			mid_x = positions[len(positions)//2][0]
			helpers_added = build_helper_column_towards_support(mid_x, y)
			if not helpers_added and not has_support_near(mid_x, y):
				# cannot make it reachable from player/ground/platforms, skip placement
				continue

		# finalize placement: add helpers (already in placed_set) and platform blocks
		for h in helpers_added:
			placed.append(h)
			occupied.add((h.rect.x, h.rect.y))

		for (px, py) in positions:
			b = Block(px, py, block_size)
			placed.append(b)
			placed_set.add((px, py))
			occupied.add((px, py))

	return placed