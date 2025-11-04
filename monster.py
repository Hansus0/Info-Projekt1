import pygame
from settings import PLAYER_VEL, FPS, BLOCK_SIZE

class Monster:
    """
    Regular enemy that chases the player.
    - Green square.
    - Spawns on top of platforms.
    - Can fly/jump toward player.
    - 1 HP.
    - Deals 10 HP/sec on contact.
    """
    COLOR = (0, 150, 0)
    SIZE = (50, 50)
    SPEED = PLAYER_VEL * 1.5
    DAMAGE = 10.0
    HP = 1

    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, self.SIZE[0], self.SIZE[1])
        self.image = pygame.Surface(self.SIZE, pygame.SRCALPHA)
        pygame.draw.rect(self.image, self.COLOR, (0, 0, self.SIZE[0], self.SIZE[1]))
        self.mask = pygame.mask.from_surface(self.image)
        self.x_vel = 0
        self.y_vel = 0
        self.dir = 1  # 1=right, -1=left
        self.hp = self.HP

    def update(self, dt, objects=None, player=None):
        """
        Move toward the player each frame.
        objects: all platforms/blocks
        player: Player instance
        """
        if player is None:
            return

        # Vector toward player
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery

        dist = (dx**2 + dy**2)**0.5
        if dist != 0:
            self.x_vel = dx / dist * self.SPEED
            self.y_vel = dy / dist * self.SPEED

        # Move
        self.rect.x += int(self.x_vel * dt * FPS / 60)
        self.rect.y += int(self.y_vel * dt * FPS / 60)

        # Update facing direction
        self.dir = 1 if dx > 0 else -1

        # Redraw
        self.image.fill((0, 0, 0, 0))
        pygame.draw.rect(self.image, self.COLOR, (0, 0, self.SIZE[0], self.SIZE[1]))
        eye_pos = (self.SIZE[0] - 15 if self.dir > 0 else 15, self.SIZE[1] // 2)
        pygame.draw.circle(self.image, (255, 255, 0), eye_pos, 8)
        self.mask = pygame.mask.from_surface(self.image)

    def draw(self, window, offset_x=0, offset_y=0):
        window.blit(self.image, (self.rect.x - offset_x, self.rect.y - offset_y))

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            return True  # dead
        return False

class Boss(Monster):
    """
    Grounded boss:
    - Larger green square.
    - Stays on platforms, walks toward player.
    - Can jump over gaps/blocks.
    - 100 HP.
    - Deals 20 HP/sec on contact.
    """
    COLOR = (0, 100, 0)
    SIZE = (100, 100)
    SPEED = PLAYER_VEL
    DAMAGE = 20.0
    HP = 100
    JUMP_FORCE = -PLAYER_VEL * 4

    def __init__(self, x, y):
        super().__init__(x, y)
        self.rect.width = self.SIZE[0]
        self.rect.height = self.SIZE[1]
        self.hp = self.HP
        self.on_ground = False

    def update(self, dt, objects=None, player=None):
        """
        Move along the ground toward player, jumping over gaps.
        """
        if player is None or objects is None:
            return

        # Horizontal movement toward player
        if player.rect.centerx > self.rect.centerx:
            self.x_vel = self.SPEED
            self.dir = 1
        else:
            self.x_vel = -self.SPEED
            self.dir = -1

        # Gravity
        self.y_vel += 1  # simple gravity
        self.on_ground = False

        # Check collisions with platforms to stay grounded
        for obj in objects:
            if hasattr(obj, 'rect') and self.rect.colliderect(obj.rect):
                # Land on top
                if self.y_vel >= 0 and self.rect.bottom <= obj.rect.bottom:
                    self.rect.bottom = obj.rect.top
                    self.y_vel = 0
                    self.on_ground = True

        # Jump toward player if obstacle detected
        if self.on_ground:
            # check if there is a block ahead
            front_rect = self.rect.copy()
            front_rect.x += self.dir * BLOCK_SIZE
            for obj in objects:
                if hasattr(obj, 'rect') and front_rect.colliderect(obj.rect):
                    self.y_vel = self.JUMP_FORCE
                    break

        # Move
        self.rect.x += int(self.x_vel * dt * FPS / 60)
        self.rect.y += int(self.y_vel * dt * FPS / 60)

        # Redraw
        self.image.fill((0, 0, 0, 0))
        pygame.draw.rect(self.image, self.COLOR, (0, 0, self.SIZE[0], self.SIZE[1]))
        eye_pos = (self.SIZE[0] - 20 if self.dir > 0 else 20, self.SIZE[1] // 2)
        pygame.draw.circle(self.image, (255, 255, 0), eye_pos, 12)
        self.mask = pygame.mask.from_surface(self.image)