import os
import random
import math
import pygame
from os import listdir
from os.path import isfile, join
pygame.init()

# Window title
pygame.display.set_caption("Platformer")

# Screen dimensions and game settings
WIDTH, HEIGHT = 1000, 800  # screen size in pixels
FPS = 60                  # frames per second
PLAYER_VEL = 5            # horizontal movement speed

# Regeneration rates (per second)
HEALTH_REGEN_RATE = 1.0    # health points per second
STAMINA_REGEN_RATE = 8.0   # stamina per second
MANA_REGEN_RATE = 4.0      # mana per second

# Main display surface
window = pygame.display.set_mode((WIDTH, HEIGHT))


# Utility: flip sprite surfaces horizontally (not used for cube but kept for assets)
def flip(sprites):
    """Return horizontally flipped copies of sprite Surfaces."""
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


# Load sprite sheets from assets on disk (keeps original project support)
def load_sprite_sheets(dir1, dir2, width, height, direction=False):
    """
    Load and slice spritesheets located at assets/dir1/dir2.
    - width,height: size of each frame in the sheet
    - direction: if True, also generate left/right flipped variants
    Returns a dict mapping names to lists of Surfaces.
    """
    path = join("assets", dir1, dir2)
    images = [f for f in listdir(path) if isfile(join(path, f))]

    all_sprites = {}

    for image in images:
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()

        sprites = []
        # slice horizontally by frame width
        for i in range(sprite_sheet.get_width() // width):
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            rect = pygame.Rect(i * width, 0, width, height)
            surface.blit(sprite_sheet, (0, 0), rect)
            sprites.append(pygame.transform.scale2x(surface))

        # store sprites, optionally with left/right variants
        if direction:
            all_sprites[image.replace(".png", "") + "_right"] = sprites
            all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
        else:
            all_sprites[image.replace(".png", "")] = sprites

    return all_sprites


def get_block(size):
    """
    Return a block Surface taken from the terrain tilesheet.
    This is used to draw ground/platform visuals.
    """
    path = join("assets", "Terrain", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    # Take a specific tile region from the tilesheet (index chosen by original project)
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
    COLOR = (255, 0, 0)
    GRAVITY = 1
    SPRITES = load_sprite_sheets("MainCharacters", "MaskDude", 32, 32, True)
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

    def loop(self, fps):
        """
        Per-frame update:
        - apply a simple gravity increment (scaled using fall_count/fps)
        - move according to velocities
        - manage hit timer
        - increment fall counter
        - update animation sprite (if sprites are used)
        """
        # If holding a ledge, freeze motion and don't apply gravity/movement.
        if self.holding:
            # keep velocities zero while holding; fall counter paused
            self.x_vel = 0
            self.y_vel = 0
            if self.hit:
                self.hit_count += 1
            if self.hit_count > fps * 2:
                self.hit = False
                self.hit_count = 0
            # Update sprite but do not advance fall_count
            self.update_sprite()
            return

        # Default behavior when not holding
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
        sprites = self.SPRITES[sprite_sheet_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[sprite_index]
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
        # snap player next to ledge in world coordinates
        if side == "right":
            # block is to the right of player, snap player to block's left side
            self.rect.x = block.rect.left - self.rect.width - 1
        else:
            # block is to the left of player, snap player to block's right side
            self.rect.x = block.rect.right + 1
        # allow one more jump while holding
        self.jump_count = 1
        # reset fall counter
        self.fall_count = 0

    def end_hold(self):
        """Release ledge hold and resume normal physics."""
        self.holding = False
        self.hold_time = 0.0
        self.hold_block = None
        self.hold_side = None
        # do not alter velocities here beyond letting gravity take effect next frame


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


class Fire(Object):
    """Animated fire trap that can be toggled on/off."""
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "fire")
        self.fire = load_sprite_sheets("Traps", "Fire", width, height)
        self.image = self.fire["off"][0]
        self.mask = pygame.mask.from_surface(self.image)
        self.animation_count = 0
        self.animation_name = "off"

    def on(self):
        """Enable fire animation (dangerous)."""
        self.animation_name = "on"

    def off(self):
        """Disable fire animation (safe)."""
        self.animation_name = "off"

    def loop(self):
        """Advance animation and update mask/rect every frame."""
        sprites = self.fire[self.animation_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        # Update rect/mask to match the current frame
        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)

        # Reset animation counter if it grows too large
        if self.animation_count // self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0


def get_background(name):
    """
    Load a background image and compute tiling positions so the background fills the screen.
    Returns (tiles, image) where tiles is a list of top-left positions to blit the image.
    """
    image = pygame.image.load(join("assets", "Background", name))
    _, _, width, height = image.get_rect()
    tiles = []

    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            pos = (i * width, j * height)
            tiles.append(pos)

    return tiles, image

#Klasse Zombie, die den Spieler jagt
class Zombie(pygame.sprite.Sprite):
    def __init__(self, x, y, width=PLAYER_WIDTH, height=PLAYER_HEIGHT):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill((30, 120, 10))  # grünlicher Block als Platzhalter
        self.rect = self.image.get_rect(topleft=(x, y))

        self.speed = 1   # normale Geschwindigkeit (langsam)
        self.direction = random.choice([-1, 1])  # Start: links oder rechts
        self.detection_range = 400
        self.damage = 1

        self.vel_y = 0  # einfache Schwerkraft

    def update(self, player, objects, block_size):
        # --- Gravitations-Logik ---
        self.vel_y += 1  # Schwerkraft
        self.rect.y += self.vel_y
        on_ground = False
        for obj in objects:
            if isinstance(obj, Block) and self.rect.colliderect(obj.rect):
                if self.vel_y > 0:  # Landet auf Block
                    self.rect.bottom = obj.rect.top
                    self.vel_y = 0
                    on_ground = True

        # --- Spieler-Distanz ---
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = abs(dx) + abs(dy)

        if distance < self.detection_range:
            # Spieler im Umkreis -> Zombie jagt ihn doppelt so schnell
            step = self.speed * 2
            if dx < 0:
                self.rect.x -= step
                self.direction = -1
            else:
                self.rect.x += step
                self.direction = 1
        else:
            # Zufällig langsam nach links/rechts
            self.rect.x += self.direction * self.speed

            # Abgrund-KI: prüfen ob Boden unter den Füßen ist
            foot_x = self.rect.centerx + self.direction * (self.rect.width // 2)
            foot_y = self.rect.bottom + 5
            tile_x = (foot_x // block_size) * block_size
            tile_y = (foot_y // block_size) * block_size

            solid_below = any(
                isinstance(obj, Block) and obj.rect.collidepoint(foot_x, foot_y)
                for obj in objects
            )
            if not solid_below:
                self.direction *= -1  # umkehren am Abgrund

        # --- Kollision mit Spieler ---
        if self.rect.colliderect(player.rect):
            player.health -= self.damage

    def draw(self, window, offset_x):
        window.blit(self.image, (self.rect.x - offset_x, self.rect.y))


# UI class draws HUD elements: bars, icons, minimap, ability/inventory boxes
class UI:
    def __init__(self, player, objects):
        # store references to player and world objects for minimap
        self.player = player
        self.objects = objects
        # example resource values
        self.health = 75
        self.max_health = 100
        self.stamina = 40
        self.max_stamina = 100
        self.mana = 60
        self.max_mana = 100
        self.buffs = [("Poison", (0, 255, 0)), ("Berserk", (255, 0, 0))]
        self.character_name = "Cube"
        # simple colored portrait surface (replace with art if available)
        self.portrait = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.rect(self.portrait, (200, 200, 255), (0, 0, 64, 64))
        # abilities and inventory are placeholders for the HUD
        self.abilities = [
            {"name": "Dash", "key": "Q", "cooldown": 2, "max_cd": 5},
            {"name": "Shield", "key": "E", "cooldown": 0, "max_cd": 8},
            {"name": "Blast", "key": "R", "cooldown": 5, "max_cd": 10},
        ]
        self.inventory = [
            {"name": "Potion", "icon": (255, 0, 0)},
            {"name": "Bomb", "icon": (150, 150, 150)},
        ]
        self.defence = 12
        self.evasion = 8

        # Inventory state
        self.inventory_open = False
        self.inventory_tab = "Inventory"  # "Inventory", "Skills", "Magic"

        # Options overlay state
        self.options_open = False
        self.options_tab = "Settings"  # "Settings" or "Keybindings"

        # Available resolutions and current selection index (default includes current WIDTH/HEIGHT)
        self.resolutions = [(800, 600), (1000, 800), (1280, 720), (1366, 768), (1920, 1080)]
        try:
            self.res_index = next(i for i, r in enumerate(self.resolutions) if r == (WIDTH, HEIGHT))
        except StopIteration:
            self.res_index = 1

        # Fullscreen flag
        self.fullscreen = False

        # Keybindings map (display only)
        self.keybindings_map = {
            "Move Left": pygame.K_LEFT,
            "Move Right": pygame.K_RIGHT,
            "Jump": pygame.K_SPACE,
            "Inventory": pygame.K_i,
            "Options": pygame.K_o,
            "Dash": pygame.K_q,
            "Shield": pygame.K_e,
            "Blast": pygame.K_r,
        }

        # transient rects used for click handling (filled each frame in draw_options)
        self.options_tab_rects = {}
        self.options_control_rects = {}

    def draw_bar(self, win, x, y, w, h, value, max_value, color, label):
        """
        Draw a labeled bar with a translucent background and border.
        - value/max_value controls fill ratio.
        """
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 120))   # translucent box so gameplay remains visible
        win.blit(s, (x, y))
        ratio = value / max_value
        pygame.draw.rect(win, color, (x+4, y+4, int((w-8)*ratio), h-8))
        pygame.draw.rect(win, (255,255,255), (x, y, w, h), 2)
        font = pygame.font.SysFont("arial", 18)
        # show whole numbers (rounded) for bar status
        txt = font.render(f"{label}: {int(round(value))}/{int(round(max_value))}", True, (255,255,255))
        win.blit(txt, (x + 8, y + h//2 - 10))

    def draw_minimap(self, win, offset_x):
        """
        Draw a simple minimap that shows blocks and player position.
        - The minimap maps a band of world coordinates centered on the camera to the minimap box.
        """
        mm_w, mm_h = 180, 140
        mm_x, mm_y = WIDTH-30-mm_w, 30
        s = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
        s.fill((0,0,0,120))
        win.blit(s, (mm_x, mm_y))
        pygame.draw.rect(win, (200,200,255), (mm_x+10, mm_y+10, mm_w-20, mm_h-20), 2)
        font = pygame.font.SysFont("arial", 18)
        win.blit(font.render("Minimap", True, (255,255,255)), (mm_x+40, mm_y+10))

        # Determine the world band the minimap represents (a bit larger than screen)
        world_x_min = offset_x - 200
        world_x_max = offset_x + WIDTH + 200
        world_y_min = 0
        world_y_max = HEIGHT

        # Draw small squares for each Block that lies in the minimap band
        for obj in self.objects:
            if isinstance(obj, Block):
                bx = obj.rect.x
                by = obj.rect.y
                if world_x_min <= bx <= world_x_max and world_y_min <= by <= world_y_max:
                    rel_x = (bx - world_x_min) / (world_x_max - world_x_min)
                    rel_y = (by - world_y_min) / (world_y_max - world_y_min)
                    px = int(mm_x+10 + rel_x*(mm_w-20))
                    py = int(mm_y+10 + rel_y*(mm_h-20))
                    pygame.draw.rect(win, (180,180,180), (px, py, 6, 6))

        # Draw player's relative position as a red circle
        bx = self.player.rect.x
        by = self.player.rect.y
        rel_x = (bx - world_x_min) / (world_x_max - world_x_min)
        rel_y = (by - world_y_min) / (world_y_max - world_y_min)
        px = int(mm_x+10 + rel_x*(mm_w-20))
        py = int(mm_y+10 + rel_y*(mm_h-20))
        pygame.draw.circle(win, (255,0,0), (px, py), 8)

    def toggle_inventory(self):
        """Open/close inventory overlay."""
        self.inventory_open = not self.inventory_open

    def cycle_tab(self):
        """Cycle inventory tabs: Inventory -> Skills -> Magic."""
        tabs = ["Inventory", "Skills", "Magic"]
        idx = tabs.index(self.inventory_tab)
        self.inventory_tab = tabs[(idx + 1) % len(tabs)]

    def toggle_options(self):
        """Open/close options overlay."""
        self.options_open = not self.options_open
        # ensure inventory is closed when options opens (avoid UI overlap)
        if self.options_open:
            self.inventory_open = False

    def draw_inventory(self, win):
        """
        Draw the inventory overlay when open.
        - Left: equipment slots
        - Right: storage grid (10 slots)
        - Top: tabs for Inventory / Skills / Magic (TAB to cycle or click)
        """
        if not self.inventory_open:
            return

        # overlay box (semi-transparent)
        w, h = 700, 450
        x = WIDTH // 2 - w // 2
        y = HEIGHT // 2 - h // 2
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((10, 10, 10, 220))
        win.blit(overlay, (x, y))

        font = pygame.font.SysFont("arial", 20)
        # Tabs
        tabs = ["Inventory", "Skills", "Magic"]
        tab_w = 140
        # reset tab rects each frame
        self.tab_rects = {}
        for i, t in enumerate(tabs):
            tx = x + 10 + i * (tab_w + 6)
            ty = y + 8
            tab_s = pygame.Surface((tab_w, 32), pygame.SRCALPHA)
            tab_s.fill((30, 30, 30, 200) if self.inventory_tab != t else (80, 80, 80, 230))
            win.blit(tab_s, (tx, ty))
            txt = font.render(t, True, (255, 255, 255))
            win.blit(txt, (tx + 8, ty + 6))
            # store clickable rect
            self.tab_rects[t] = pygame.Rect(tx, ty, tab_w, 32)

        # Draw currently selected tab contents
        content_x = x + 16
        content_y = y + 56

        if self.inventory_tab == "Inventory":
            # Equipment (left column)
            eq_x = content_x
            eq_y = content_y
            win.blit(font.render("Equipment", True, (255,255,255)), (eq_x, eq_y))
            eq_y += 28
            slot_h = 40
            for slot_name, item in self.equipment.items():
                slot_rect = pygame.Rect(eq_x, eq_y, 220, slot_h)
                s = pygame.Surface((slot_rect.w, slot_rect.h), pygame.SRCALPHA)
                s.fill((40,40,40,200))
                win.blit(s, slot_rect.topleft)
                win.blit(font.render(slot_name, True, (220,220,220)), (eq_x + 6, eq_y + 8))
                if item:
                    win.blit(font.render(item.get("name","item"), True, (200,255,200)), (eq_x + 120, eq_y + 8))
                eq_y += slot_h + 8

            # Storage (right area) 10 slots (2 rows x 5)
            st_x = x + w - 16 - (5 * 64)  # right-aligned
            st_y = content_y
            win.blit(font.render("Storage", True, (255,255,255)), (st_x, st_y))
            st_y += 28
            slot_size = 56
            padding = 8
            for i in range(10):
                row = i // 5
                col = i % 5
                sx = st_x + col * (slot_size + padding)
                sy = st_y + row * (slot_size + padding)
                s = pygame.Surface((slot_size, slot_size), pygame.SRCALPHA)
                s.fill((60,60,60,200))
                win.blit(s, (sx, sy))
                item = self.storage[i]
                if item:
                    # draw colored rect as icon placeholder
                    pygame.draw.rect(win, item.get("icon", (200,200,200)), (sx+6, sy+6, slot_size-12, slot_size-12))
                    win.blit(font.render(item.get("name","x")[:6], True, (255,255,255)), (sx+4, sy+slot_size-18))

        elif self.inventory_tab == "Skills":
            tx = content_x
            ty = content_y
            win.blit(font.render("Skills", True, (255,255,255)), (tx, ty))
            ty += 28
            for s_name in self.skills:
                win.blit(font.render("• " + s_name, True, (220,220,220)), (tx + 8, ty))
                ty += 26

        elif self.inventory_tab == "Magic":
            tx = content_x
            ty = content_y
            win.blit(font.render("Magic Spells", True, (255,255,255)), (tx, ty))
            ty += 28
            for m_name in self.magic:
                win.blit(font.render("• " + m_name, True, (220,220,220)), (tx + 8, ty))
                ty += 26

    def draw_options(self, win):
        """Render the options overlay (Settings / Keybindings)."""
        if not self.options_open:
            return

        w, h = 600, 380
        x = WIDTH // 2 - w // 2
        y = HEIGHT // 2 - h // 2
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((12, 12, 12, 230))
        win.blit(overlay, (x, y))

        font = pygame.font.SysFont("arial", 20)
        title = font.render("Options", True, (255, 255, 255))
        win.blit(title, (x + 16, y + 10))

        # Tabs: Settings / Keybindings
        tab_w = 140
        tabs = ["Settings", "Keybindings"]
        self.options_tab_rects = {}
        for i, t in enumerate(tabs):
            tx = x + 16 + i * (tab_w + 8)
            ty = y + 44
            tab_s = pygame.Surface((tab_w, 34), pygame.SRCALPHA)
            tab_s.fill((50, 50, 50, 220) if self.options_tab != t else (100, 100, 100, 230))
            win.blit(tab_s, (tx, ty))
            win.blit(font.render(t, True, (255, 255, 255)), (tx + 8, ty + 6))
            self.options_tab_rects[t] = pygame.Rect(tx, ty, tab_w, 34)

        content_x = x + 20
        content_y = y + 96
        small = pygame.font.SysFont("arial", 16)

        if self.options_tab == "Settings":
            # Resolution selector
            win.blit(small.render("Resolution", True, (255,255,255)), (content_x, content_y))
            rx, ry = content_x + 140, content_y - 4
            # left arrow
            left_rect = pygame.Rect(rx, ry, 28, 28)
            pygame.draw.rect(win, (80,80,80), left_rect)
            win.blit(small.render("<", True, (255,255,255)), (rx+8, ry+4))
            # current resolution display
            res_txt = f"{self.resolutions[self.res_index][0]} x {self.resolutions[self.res_index][1]}"
            win.blit(small.render(res_txt, True, (200,200,200)), (rx + 38, ry + 4))
            # right arrow
            right_rect = pygame.Rect(rx + 170, ry, 28, 28)
            pygame.draw.rect(win, (80,80,80), right_rect)
            win.blit(small.render(">", True, (255,255,255)), (right_rect.x+8, right_rect.y+4))

            # Fullscreen toggle
            fs_y = content_y + 60
            fs_rect = pygame.Rect(content_x + 140, fs_y - 4, 18, 18)
            pygame.draw.rect(win, (80,80,80), fs_rect)
            if self.fullscreen:
                pygame.draw.rect(win, (0,200,0), fs_rect.inflate(-4, -4))
            win.blit(small.render("Fullscreen", True, (255,255,255)), (fs_rect.x + 28, fs_rect.y - 2))

            # Save rects for click handling
            self.options_control_rects = {
                "res_left": left_rect,
                "res_right": right_rect,
                "fullscreen": fs_rect
            }

            # Help text
            help_txt = "Click arrows to change resolution. Toggle fullscreen to switch display mode."
            win.blit(small.render(help_txt, True, (180,180,180)), (content_x, fs_y + 40))

        elif self.options_tab == "Keybindings":
            # show keybindings list
            ky = content_y
            for name, key in self.keybindings_map.items():
                kname = pygame.key.name(key)
                win.blit(small.render(f"{name}: {kname}", True, (220,220,220)), (content_x, ky))
                ky += 26

    def handle_options_click(self, mx, my):
        """
        Process a click at (mx,my) on the options overlay.
        Returns an action dict if a resolution/fullscreen change is requested, else None.
        """
        if not self.options_open:
            return None

        # Tab clicks
        for t, rect in self.options_tab_rects.items():
            if rect.collidepoint(mx, my):
                self.options_tab = t
                return None

        # Control clicks
        for name, rect in self.options_control_rects.items():
            if rect.collidepoint(mx, my):
                # resolution left/right
                if name == "res_left":
                    self.res_index = (self.res_index - 1) % len(self.resolutions)
                    return {"set_resolution": self.resolutions[self.res_index]}
                if name == "res_right":
                    self.res_index = (self.res_index + 1) % len(self.resolutions)
                    return {"set_resolution": self.resolutions[self.res_index]}
                if name == "fullscreen":
                    self.fullscreen = not self.fullscreen
                    return {"toggle_fullscreen": self.fullscreen}
        return None

    # Update: draw() should call draw_inventory when appropriate
    def draw(self, win, offset_x):
        # Health / Stamina / Mana
        self.draw_bar(win, 30, 30, 220, 28, self.health, self.max_health, (255,0,0), "Health")
        self.draw_bar(win, 30, 65, 220, 22, self.stamina, self.max_stamina, (0,255,0), "Stamina")
        self.draw_bar(win, 30, 95, 220, 22, self.mana, self.max_mana, (0,0,255), "Mana")

        # Buff icons (simple colored circles with first letter)
        for i, (name, color) in enumerate(self.buffs):
            icon_rect = pygame.Rect(30 + i*38, 130, 32, 32)
            s = pygame.Surface((32,32), pygame.SRCALPHA)
            s.fill((0,0,0,120))
            win.blit(s, icon_rect.topleft)
            pygame.draw.circle(win, color, icon_rect.center, 14)
            font = pygame.font.SysFont("arial", 14)
            txt = font.render(name[0], True, (255,255,255))
            win.blit(txt, (icon_rect.x+9, icon_rect.y+7))

        # Bottom-left: portrait and character name + defence/evasion stats
        s = pygame.Surface((220, 80), pygame.SRCALPHA)
        s.fill((0,0,0,120))
        win.blit(s, (30, HEIGHT-110))
        win.blit(self.portrait, (40, HEIGHT-100))
        font = pygame.font.SysFont("arial", 22)
        txt = font.render(self.character_name, True, (255,255,255))
        win.blit(txt, (110, HEIGHT-80))
        font2 = pygame.font.SysFont("arial", 16)
        win.blit(font2.render(f"Defence: {self.defence}", True, (200,200,200)), (110, HEIGHT-60))
        win.blit(font2.render(f"Evasion: {self.evasion}", True, (200,200,200)), (110, HEIGHT-40))

        # Abilities bar (center bottom) with cooldowns
        ab_w = 80
        ab_h = 80
        ab_x = WIDTH//2 - (len(self.abilities)*ab_w)//2
        ab_y = HEIGHT-100
        for i, ab in enumerate(self.abilities):
            s = pygame.Surface((ab_w, ab_h), pygame.SRCALPHA)
            s.fill((0,0,0,120))
            win.blit(s, (ab_x+i*ab_w, ab_y))
            pygame.draw.rect(win, (100,100,255), (ab_x+i*ab_w+8, ab_y+8, ab_w-16, ab_h-16), 2)
            font = pygame.font.SysFont("arial", 18)
            win.blit(font.render(ab["key"], True, (255,255,0)), (ab_x+i*ab_w+10, ab_y+10))
            win.blit(font.render(ab["name"], True, (255,255,255)), (ab_x+i*ab_w+10, ab_y+35))
            cd_txt = f"{ab['cooldown']}/{ab['max_cd']}" if ab["cooldown"] > 0 else "Ready"
            win.blit(font2.render(cd_txt, True, (255,0,0) if ab["cooldown"] > 0 else (0,255,0)), (ab_x+i*ab_w+10, ab_y+60))

        # Inventory quickslots (bottom-right)
        inv_w, inv_h = 60, 60
        inv_x = WIDTH-30-len(self.inventory)*inv_w
        inv_y = HEIGHT-90
        for i, item in enumerate(self.inventory):
            s = pygame.Surface((inv_w, inv_h), pygame.SRCALPHA)
            s.fill((0,0,0,120))
            win.blit(s, (inv_x+i*inv_w, inv_y))
            pygame.draw.rect(win, item["icon"], (inv_x+i*inv_w+12, inv_y+12, inv_w-24, inv_h-24))
            font = pygame.font.SysFont("arial", 16)
            win.blit(font.render(item["name"], True, (255,255,255)), (inv_x+i*inv_w+8, inv_y+inv_h-22))

        # Minimap in the top-right
        self.draw_minimap(win, offset_x)
        # draw inventory overlay if open (on top of UI)
        self.draw_inventory(win)

        # draw options overlay on top if open
        self.draw_options(win)


# Draw the game world and UI each frame
def draw(window, background, bg_image, player, objects, offset_x, ui):
    # Tile the background to cover the screen
    for tile in background:
        window.blit(bg_image, tile)

    # Draw all world objects with camera offset applied
    for obj in objects:
        obj.draw(window, offset_x)

    # Draw the player and HUD/UI last so they appear on top
    player.draw(window, offset_x)
    ui.draw(window, offset_x)

    pygame.display.update()


# Vertical collision detection: used to resolve landings and head hits
def handle_vertical_collision(player, objects, dy):
    collided_objects = []
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            if dy > 0:
                # falling: snap player's bottom to object's top and mark landed
                player.rect.bottom = obj.rect.top
                player.landed()
            elif dy < 0:
                # rising: snap player's top to object's bottom and bounce
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

    if keys[pygame.K_LEFT] and not collide_left:
        player.move_left(PLAYER_VEL)
    if keys[pygame.K_RIGHT] and not collide_right:
        player.move_right(PLAYER_VEL)

    vertical_collide = handle_vertical_collision(player, objects, player.y_vel)
    to_check = [collide_left, collide_right, *vertical_collide]

    for obj in to_check:
        if obj and obj.name == "fire":
            player.make_hit()


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
	Manage ledge grabbing/holding:
	- Player starts holding when SPACE is held while adjacent to a block ledge and airborne.
	- While holding: player stays snapped next to the ledge, hold_time accumulates (max HOLD_MAX).
	- Releasing SPACE or exceeding HOLD_MAX ends the hold.
	- While holding the player may press UP or W to perform the extra jump.
	"""
	keys = pygame.key.get_pressed()

	# If already holding, maintain or release
	if player.holding:
		# Ensure block still exists
		if player.hold_block not in objects:
			player.end_hold()
			return

		# Release if SPACE is released
		if not keys[pygame.K_SPACE]:
			player.end_hold()
			return

		# Jump from hold with UP/W (gives one extra jump)
		if keys[pygame.K_UP] or keys[pygame.K_w]:
			player.end_hold()
			# perform jump (Player.jump will increment jump_count)
			player.jump()
			return

		# accumulate hold time and auto-release if exceeded
		player.hold_time += dt
		if player.hold_time >= player.HOLD_MAX:
			player.end_hold()
			return

		# keep player snapped to the held block
		b = player.hold_block
		if player.hold_side == "right":
			player.rect.x = b.rect.left - player.rect.width - 1
		else:
			player.rect.x = b.rect.right + 1
		player.x_vel = 0
		player.y_vel = 0
		return

	# Not holding: require SPACE held to start hold, and player must be airborne
	if not keys[pygame.K_SPACE]:
		return

	# player's airborne check: not grounded -> jump_count > 0 or y_vel != 0
	if player.jump_count == 0 and player.y_vel >= 0:
		# grounded; don't grab
		return

	# detection tolerances
	horiz_thresh = max(8, block_size // 8)  # px tolerance for being adjacent to block side
	vert_tolerance = block_size // 2  # vertical closeness to block top

	# try to find a nearby block edge to grab
	for obj in objects:
		if not isinstance(obj, Block):
			continue
		b = obj
		# right side of player near left side of block
		if abs(player.rect.right - b.rect.left) <= horiz_thresh:
			# check vertical overlap near block top
			if (player.rect.bottom > b.rect.top - vert_tolerance) and (player.rect.top < b.rect.top + vert_tolerance):
				player.start_hold(b, "right")
				return
		# left side of player near right side of block
		if abs(player.rect.left - b.rect.right) <= horiz_thresh:
			if (player.rect.bottom > b.rect.top - vert_tolerance) and (player.rect.top < b.rect.top + vert_tolerance):
				player.start_hold(b, "left")
				return

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


# Main game function: sets up world, loops, and updates
def main():
    global WIDTH, HEIGHT, window, background, bg_image
    # declare globals that may be reassigned (resolution / fullscreen)

    clock = pygame.time.Clock()
    background, bg_image = get_background("Blue.png")

    block_size = 96
    ground_y = HEIGHT - block_size  # y coordinate for ground blocks

    player = Player(100, 100, 50, 50)
    fire = Fire(100, ground_y - 64, 16, 32)
    fire.on()

    # initialize a chunk of ground; update_ground will expand/trim as needed
    floor = [Block(i * block_size, ground_y, block_size)
             for i in range(-WIDTH // block_size, (WIDTH * 2) // block_size)]
    objects = [*floor, Block(0, HEIGHT - block_size * 2, block_size),
               Block(block_size * 3, HEIGHT - block_size * 4, block_size), fire]

    # UI needs reference to player and object list for minimap
    ui = UI(player, objects)

    # occupied set tracks taken tile positions (x,y)
    occupied = set((obj.rect.x, obj.rect.y) for obj in objects if isinstance(obj, Block))

    # procedural cubes/platforms management
    cubes = []                 # list of Block objects generated as cubes/platforms
    CUBE_BATCH = 8             # try to place this many structures per spawn
    GENERATE_CHUNK = WIDTH * 2 # width of each generation chunk

    # Ensure camera offset is defined before computing spawn positions
    offset_x = 0              # camera horizontal offset (must be set before spawn cursors)

    # initial generation: cover the start screen plus margins so platforms appear immediately
    start_gen = offset_x - GENERATE_CHUNK
    end_gen = offset_x + WIDTH + GENERATE_CHUNK
    initial_batch = CUBE_BATCH * 3
    new_cubes = generate_cubes(start_gen, end_gen, initial_batch, block_size, occupied, ground_y, player.rect, max_vertical_gap=block_size * 4)
    if new_cubes:
        cubes.extend(new_cubes)
        objects.extend(new_cubes)

    # set generation cursors to the edges of the initial generated region
    next_gen_right = end_gen
    next_gen_left = start_gen

    scroll_area_width = 200   # area near screen edges that triggers camera scroll

    run = True
    while run:
        # tick and compute dt in seconds
        ms = clock.tick(FPS)
        dt = ms / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

            # Handle mouse clicks for inventory tabs and options
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ui.inventory_open:
                    mx, my = event.pos
                    for tab_name, rect in ui.tab_rects.items():
                        if rect.collidepoint(mx, my):
                            ui.inventory_tab = tab_name
                            break
                elif ui.options_open:
                    mx, my = event.pos
                    action = ui.handle_options_click(mx, my)
                    # apply returned actions
                    if action:
                        # set resolution
                        if "set_resolution" in action:
                            new_w, new_h = action["set_resolution"]
                            WIDTH, HEIGHT = new_w, new_h
                            # preserve fullscreen flag when recreating display
                            flags = pygame.FULLSCREEN if ui.fullscreen else 0
                            window = pygame.display.set_mode((WIDTH, HEIGHT), flags)
                            background, bg_image = get_background("Blue.png")
                        # toggle fullscreen
                        if "toggle_fullscreen" in action:
                            ui.fullscreen = action["toggle_fullscreen"]
                            flags = pygame.FULLSCREEN if ui.fullscreen else 0
                            window = pygame.display.set_mode((WIDTH, HEIGHT), flags)
                    # prevent clicks passing to other UI
                    continue

            # Toggle inventory with "I" and options with "O" and tab cycle with TAB; jump with SPACE
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_i:
                    ui.toggle_inventory()
                elif event.key == pygame.K_o:
                    ui.toggle_options()
                elif event.key == pygame.K_TAB and ui.inventory_open:
                    ui.cycle_tab()
                elif event.key == pygame.K_SPACE and player.jump_count < 2 and not player.holding:
                    player.jump()

        # Regenerate resources each frame (rate per second / FPS)
        ui.health = min(ui.max_health, ui.health + (HEALTH_REGEN_RATE / FPS))
        ui.stamina = min(ui.max_stamina, ui.stamina + (STAMINA_REGEN_RATE / FPS))
        ui.mana = min(ui.max_mana, ui.mana + (MANA_REGEN_RATE / FPS))

        # Per-frame updates: physics, traps, input handling
        player.loop(FPS)
        fire.loop()
        handle_move(player, objects)

        # Handle ledge grabbing/holding (uses key state and dt)
        handle_ledge_grab(player, objects, dt, block_size)

        # Keep the ground generated around the camera every frame so it appears infinite.
        update_ground(objects, block_size, offset_x, ground_y)

        # Remove cubes far behind/forward the camera and free occupied spots (both sides)
        remove_margin = WIDTH
        for c in cubes[:]:
            if c.rect.x < offset_x - remove_margin or c.rect.x > offset_x + WIDTH + remove_margin:
                if c in objects:
                    objects.remove(c)
                cubes.remove(c)
                occupied.discard((c.rect.x, c.rect.y))

        # Generate more cubes/platforms ahead and behind as the camera moves
        GENERATE_AHEAD = GENERATE_CHUNK * 2
        # generate to the right while next_gen_right is within target ahead limit
        while next_gen_right < offset_x + GENERATE_AHEAD:
            new_cubes = generate_cubes(next_gen_right, next_gen_right + GENERATE_CHUNK, CUBE_BATCH, block_size, occupied, ground_y, player.rect, max_vertical_gap=block_size * 4)
            if new_cubes:
                cubes.extend(new_cubes)
                objects.extend(new_cubes)
            next_gen_right += GENERATE_CHUNK

        # generate to the left while next_gen_left is within target behind limit
        while next_gen_left > offset_x - GENERATE_AHEAD:
            left_start = next_gen_left - GENERATE_CHUNK
            new_cubes = generate_cubes(left_start, next_gen_left, CUBE_BATCH, block_size, occupied, ground_y, player.rect, max_vertical_gap=block_size * 4)
            if new_cubes:
                cubes.extend(new_cubes)
                objects.extend(new_cubes)
            next_gen_left -= GENERATE_CHUNK

        # Center camera on player horizontally so player stays in the middle of the screen
        offset_x = int(player.rect.centerx - WIDTH // 2)

        # Draw world and UI
        draw(window, background, bg_image, player, objects, offset_x, ui)

        # (draw_options is already called inside ui.draw, so no separate call needed)
        # ...existing code...

    pygame.quit()
    quit()


# Ensure these globals exist at module level so main can reassign them safely
background = None
bg_image = None

if __name__ == "__main__":
    # main is defined without parameters; call it directly

    main()


