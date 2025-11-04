import pygame
import random
from settings import PLAYER_VEL, GRAVITY, FPS

class Monster:
    """Aggressive enemy that spawns on top of platforms and hunts the player."""
    COLOR = (0, 150, 0)  # Green color
    DEFAULT_SIZE = (40, 40)
    SPEED = PLAYER_VEL * 1.8
    DAMAGE = 10.0  # 10 HP per second
    HP = 1
    CHASE_RANGE = 1000  # Detection range in pixels
    JUMP_STRENGTH = -15
    FLYING = False  # False = ground AI (jump/climb), True = flying

    def __init__(self, x, y, w=None, h=None):
        w = w or self.DEFAULT_SIZE[0]
        h = h or self.DEFAULT_SIZE[1]
        self.rect = pygame.Rect(x, y, w, h)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(self.image, self.COLOR, (0, 0, w, h))
        self.mask = pygame.mask.from_surface(self.image)
        self.dir = 1
        self.x_vel = 0
        self.y_vel = 0
        self.on_ground = False
        self._since_attack = 0
        self.health = self.HP

    @staticmethod
    def spawn_on_platform(platforms):
        """Pick a random platform and spawn the monster on top of it."""
        platform = random.choice(platforms)
        x = random.randint(platform.rect.left, platform.rect.right - 40)
        y = platform.rect.top - 40
        return x, y

    def update(self, dt, platforms, player):
        """Update monster behavior: chase, gravity, movement."""
        self._since_attack += dt
        if not player:
            return

        # Distance to player
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = (dx**2 + dy**2) ** 0.5

        if dist < self.CHASE_RANGE:
            # Horizontal chase
            if dx > 5:
                self.x_vel = self.SPEED
                self.dir = 1
            elif dx < -5:
                self.x_vel = -self.SPEED
                self.dir = -1
            else:
                self.x_vel = 0

            if self.FLYING:
                # Flying monsters move freely toward player
                self.y_vel = (dy / abs(dy)) * self.SPEED if dy != 0 else 0
            else:
                # Ground monsters jump toward higher platforms
                if dy < -60 and self.on_ground:
                    self.y_vel = self.JUMP_STRENGTH

        # Gravity
        if not self.FLYING:
            self.y_vel += GRAVITY * dt

        # Movement
        self.rect.x += int(self.x_vel * dt * FPS / 60)
        self.rect.y += int(self.y_vel * dt * FPS / 60)

        # Platform collision (grounded logic)
        self.on_ground = False
        if not self.FLYING:
            for p in platforms:
                if self.rect.colliderect(p.rect) and self.y_vel >= 0:
                    if self.rect.bottom <= p.rect.bottom:
                        self.rect.bottom = p.rect.top
                        self.y_vel = 0
                        self.on_ground = True

        # Redraw based on direction
        w, h = self.rect.size
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(self.image, self.COLOR, (0, 0, w, h))
        eye_color = (255, 255, 0)
        pygame.draw.circle(
            self.image, eye_color,
            (w - 10 if self.dir > 0 else 10, h // 2), 6
        )

    def draw(self, window, offset_x=0, offset_y=0):
        """Draw the monster with camera offset."""
        window.blit(self.image, (self.rect.x - offset_x, self.rect.y - offset_y))

    def attack_player(self, player, dt):
        """Deal damage to player if touching them."""
        if self.rect.colliderect(player.rect):
            player.health -= self.DAMAGE * dt

    def take_damage(self, amount):
        self.health -= amount
        return self.health <= 0  # Return True if dead


class Boss(Monster):
    """Stronger flying monster with more health and damage."""
    COLOR = (180, 0, 0)
    DEFAULT_SIZE = (80, 80)
    SPEED = PLAYER_VEL * 1.5
    DAMAGE = 15.0
    HP = 10
    FLYING = True  # Boss can fly

    def __init__(self, x, y, w=None, h=None):
        super().__init__(x, y, w or self.DEFAULT_SIZE[0], h or self.DEFAULT_SIZE[1])
        self.health = self.HP
        self.max_health = self.HP

    def draw(self, window, offset_x=0, offset_y=0):
        """Draw the boss with a simple HP bar."""
        super().draw(window, offset_x, offset_y)
        bar_width = self.rect.width
        bar_height = 6
        health_ratio = max(self.health / self.max_health, 0)
        pygame.draw.rect(window, (255, 0, 0), 
                         (self.rect.x - offset_x, self.rect.y - offset_y - 10, bar_width, bar_height))
        pygame.draw.rect(window, (0, 255, 0), 
                         (self.rect.x - offset_x, self.rect.y - offset_y - 10, bar_width * health_ratio, bar_height))