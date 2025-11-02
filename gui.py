import pygame
import random
from os.path import join
from settings import WIDTH, HEIGHT, BLOCK_SIZE
from player import Block
from monster import Monster

def get_background(name):
    """Create background image and return it with tile positions."""
    image = pygame.image.load(join("Assets", "Background", name))
    _, _, width, height = image.get_rect()
    tiles = []
    
    for i in range(WIDTH // width + 2):
        for j in range(HEIGHT // height + 2):
            tiles.append((i * width, j * height))
            
    return tiles, image


class UI:
    def __init__(self, player, objects):
        self.player = player
        self.objects = objects
        self.health = 100
        self.max_health = 100
        self.stamina = 100
        self.max_stamina = 100
        self.mana = 100
        self.max_mana = 100
        self.character_name = "my"
        self.portrait = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.rect(self.portrait, (200, 200, 255), (0, 0, 64, 64))
        self.damage_flash = 0  # For damage indication
        
        self.abilities = [
            {"name": "Dash", "key": "Q", "cooldown": 0, "max_cd": self.player.DASH_COOLDOWN},
        ]
        
        self.inventory = []
        self.inventory_open = False
        self.inventory_tab = "Inventory"
        self.options_open = False
        self.options_tab = "Settings"
        
        self.resolutions = [(800, 600), (1000, 800), (1280, 720), (1366, 768), (1920, 1080)]
        try:
            self.res_index = next(i for i, r in enumerate(self.resolutions) if r == (WIDTH, HEIGHT))
        except StopIteration:
            self.res_index = 1
            
        self.fullscreen = False
        self.equipment = {}
        self.skills = []
        self.magic = []
        self.storage = [None] * 10
        
        self.keybindings_map = {
            "Move Left": pygame.K_a,
            "Move Right": pygame.K_d,
            "Jump": pygame.K_SPACE,
            "Inventory": pygame.K_i,
            "Options": pygame.K_o,
            "Dash": pygame.K_q,
        }
        
        self.options_tab_rects = {}
        self.options_control_rects = {}
        self.tab_rects = {}

        # Simplified minimap
        self.minimap_scale = 0.1
        self.minimap_width = int(WIDTH * 0.2)
        self.minimap_height = int(HEIGHT * 0.15)
        self.minimap_surface = pygame.Surface((self.minimap_width, self.minimap_height))
        self.minimap_rect = pygame.Rect(WIDTH - self.minimap_width - 10, 10, 
                                      self.minimap_width, self.minimap_height)

    def draw_bar(self, win, x, y, w, h, value, max_value, color, label):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 120))
        win.blit(s, (x, y))
        ratio = max(0, min(1, value / max_value))
        pygame.draw.rect(win, color, (x+4, y+4, int((w-8)*ratio), h-8))
        pygame.draw.rect(win, (255,255,255), (x, y, w, h), 2)
        font = pygame.font.SysFont("arial", 18)
        txt = font.render(f"{label}: {int(round(value))}/{int(round(max_value))}", True, (255,255,255))
        win.blit(txt, (x + 8, y + h//2 - 10))

    def update_minimap(self, player, objects, camera_x, camera_y, monsters=None):
        """Show what's ahead of the player including monsters."""
        self.minimap_surface.fill((50, 150, 255))  # Sky blue
        
        # Show a much larger area ahead of player
        view_range = self.minimap_width / self.minimap_scale * 3  # Increased view range by 3x
        
        # Player position in world
        player_world_x = player.rect.centerx
        player_world_y = player.rect.centery
        
        # Minimap shows from player position forward with extended range
        map_start_x = player_world_x - view_range * 0.2  # Show a bit behind player
        map_end_x = player_world_x + view_range * 0.8    # Show more ahead
        
        # Draw all objects in the extended view
        for obj in objects:
            if isinstance(obj, Block):
                # Show blocks in the extended range
                if map_start_x <= obj.rect.centerx <= map_end_x:
                    # Map to minimap coordinates (player at left edge)
                    rel_x = ((obj.rect.x - map_start_x) / (map_end_x - map_start_x)) * self.minimap_width
                    rel_y = (obj.rect.y - player_world_y) * self.minimap_scale + self.minimap_height / 2
                    
                    if 0 <= rel_x < self.minimap_width and 0 <= rel_y < self.minimap_height:
                        block_w = max(2, obj.rect.width * self.minimap_scale)
                        block_h = max(2, obj.rect.height * self.minimap_scale)
                        pygame.draw.rect(self.minimap_surface, (100, 100, 100),
                                      (rel_x, rel_y, block_w, block_h))
        
        # Draw monsters in the extended view
        if monsters:
            for monster in monsters:
                if map_start_x <= monster.rect.centerx <= map_end_x:
                    rel_x = ((monster.rect.centerx - map_start_x) / (map_end_x - map_start_x)) * self.minimap_width
                    rel_y = (monster.rect.centery - player_world_y) * self.minimap_scale + self.minimap_height / 2
                    
                    if 0 <= rel_x < self.minimap_width and 0 <= rel_y < self.minimap_height:
                        pygame.draw.circle(self.minimap_surface, (255, 100, 0),
                                         (int(rel_x), int(rel_y)), 3)
        
        # Draw player position on minimap
        player_minimap_x = self.minimap_width * 0.2  # Position player at 20% from left
        player_minimap_y = self.minimap_height / 2
        pygame.draw.circle(self.minimap_surface, (255, 0, 0),
                         (int(player_minimap_x), int(player_minimap_y)), 4)

    def draw_minimap(self, win, offset_x):
        win.blit(self.minimap_surface, self.minimap_rect)
        pygame.draw.rect(win, (255, 255, 255), self.minimap_rect, 2)

    def toggle_inventory(self):
        self.inventory_open = not self.inventory_open

    def cycle_tab(self):
        tabs = ["Inventory", "Skills", "Magic"]
        idx = tabs.index(self.inventory_tab)
        self.inventory_tab = tabs[(idx + 1) % len(tabs)]

    def toggle_options(self):
        self.options_open = not self.options_open
        if self.options_open:
            self.inventory_open = False

    def draw_inventory(self, win):
        if not self.inventory_open:
            return
        w, h = 700, 450
        x = WIDTH // 2 - w // 2
        y = HEIGHT // 2 - h // 2
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((10, 10, 10, 220))
        win.blit(overlay, (x, y))
        
        font = pygame.font.SysFont("arial", 20)
        title = font.render("Inventory", True, (255, 255, 255))
        win.blit(title, (x + 16, y + 10))

    def draw_options(self, win):
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
            win.blit(small.render("Resolution", True, (255,255,255)), (content_x, content_y))
            rx, ry = content_x + 140, content_y - 4
            left_rect = pygame.Rect(rx, ry, 28, 28)
            pygame.draw.rect(win, (80,80,80), left_rect)
            win.blit(small.render("<", True, (255,255,255)), (rx+8, ry+4))
            
            res_txt = f"{self.resolutions[self.res_index][0]} x {self.resolutions[self.res_index][1]}"
            win.blit(small.render(res_txt, True, (200,200,200)), (rx + 38, ry + 4))
            
            right_rect = pygame.Rect(rx + 170, ry, 28, 28)
            pygame.draw.rect(win, (80,80,80), right_rect)
            win.blit(small.render(">", True, (255,255,255)), (right_rect.x+8, right_rect.y+4))

            fs_y = content_y + 60
            fs_rect = pygame.Rect(content_x + 140, fs_y - 4, 18, 18)
            pygame.draw.rect(win, (80,80,80), fs_rect)
            if self.fullscreen:
                pygame.draw.rect(win, (0,200,0), fs_rect.inflate(-4, -4))
            win.blit(small.render("Fullscreen", True, (255,255,255)), (fs_rect.x + 28, fs_rect.y - 2))

            self.options_control_rects = {
                "res_left": left_rect,
                "res_right": right_rect,
                "fullscreen": fs_rect
            }

        elif self.options_tab == "Keybindings":
            ky = content_y
            for name, key in self.keybindings_map.items():
                kname = pygame.key.name(key)
                win.blit(small.render(f"{name}: {kname}", True, (220,220,220)), (content_x, ky))
                ky += 26

    def handle_options_click(self, mx, my):
        if not self.options_open:
            return None
        for t, rect in self.options_tab_rects.items():
            if rect.collidepoint(mx, my):
                self.options_tab = t
                return None
        for name, rect in self.options_control_rects.items():
            if rect.collidepoint(mx, my):
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

    def draw(self, win, offset_x):
        # Damage flash effect
        if self.damage_flash > 0:
            flash_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            alpha = int(self.damage_flash * 100)
            flash_surface.fill((255, 0, 0, alpha))
            win.blit(flash_surface, (0, 0))
            self.damage_flash = max(0, self.damage_flash - 0.05)
        
        # Main HUD
        self.draw_bar(win, 30, 30, 220, 28, self.health, self.max_health, (255,0,0), "Health")
        self.draw_bar(win, 30, 65, 220, 22, self.stamina, self.max_stamina, (0,255,0), "Stamina")
        self.draw_bar(win, 30, 95, 220, 22, self.mana, self.max_mana, (0,0,255), "Mana")

        # Ability icons
        font2 = pygame.font.SysFont("arial", 16)
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

            # Update cooldown from player
            current_cd = round(self.player.dash_cooldown_timer, 1)
            is_ready = current_cd >= ab['max_cd']
            cd_txt = "Ready" if is_ready else f"{current_cd}/{ab['max_cd']}"
            win.blit(font2.render(cd_txt, True, (0,255,0) if is_ready else (255,0,0)),
                    (ab_x+i*ab_w+10, ab_y+55))

        self.draw_minimap(win, offset_x)
        self.draw_inventory(win)
        self.draw_options(win)


def draw(window, background, bg_image, player, objects, offset_x, ui, monsters=None, camera_y=0):
    """Draw world with horizontal scrolling only."""
    bg_width = bg_image.get_width()
    bg_height = bg_image.get_height()
    
    tiles_x = WIDTH // bg_width + 2
    tiles_y = HEIGHT // bg_height + 2
    
    # Draw background
    for y in range(tiles_y):
        for x in range(tiles_x):
            bg_x = x * bg_width - (offset_x * 0.3) % bg_width
            bg_y = y * bg_height
            window.blit(bg_image, (int(bg_x), int(bg_y)))

    # Draw objects
    for obj in objects:
        if not getattr(obj, 'invisible', False):
            window.blit(obj.image, (obj.rect.x - offset_x, obj.rect.y - camera_y))

    # Draw monsters
    if monsters:
        for monster in monsters:
            monster.draw(window, offset_x, camera_y)

    # Draw player
    window.blit(player.sprite, (player.rect.x - offset_x, player.rect.y - camera_y))

    # Draw UI
    ui.draw(window, offset_x)

    pygame.display.update()


def spawn_monsters_on_surfaces(objects, num_monsters=3, monster_size=(40,40)):
    """Spawn monsters on platform surfaces."""
    blocks = [o for o in objects if isinstance(o, Block)]
    if not blocks:
        return []

    choices = random.sample(blocks, min(num_monsters, len(blocks)))
    monsters = []
    
    for b in choices:
        mw, mh = monster_size
        mx = b.rect.x + (b.rect.width - mw) // 2
        my = b.rect.y - mh
        mon = Monster(mx, my, mw, mh)
        mon.dir = random.choice([-1, 1])
        monsters.append(mon)

    return monsters