import pygame
import random
from settings import PLAYER_VEL, FPS

class Monster:
    """Aggressive enemy that hunts the player."""
    COLOR = (0, 150, 0)  # Green color
    DEFAULT_SIZE = (40, 40)  # Square shape
    SPEED = PLAYER_VEL * 2  # Double the player's speed
    DAMAGE = 10.0  # 10 health per second
    CHASE_RANGE = float('inf')  # Chase forever
    HP = 1  # Only 1 HP

    def __init__(self, x, y, w=None, h=None):
        w = w or self.DEFAULT_SIZE[0]
        h = h or self.DEFAULT_SIZE[1]
        self.rect = pygame.Rect(x, y, w, h)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        self.dir = random.choice([-1, 1])  # Initialize direction randomly (1 = right, -1 = left)
        pygame.draw.rect(self.image, self.COLOR, (0, 0, w, h))
        # Draw "eye" to show direction
        eye_color = (255, 255, 0)  # Yellow eye
        eye_size = 8
        pygame.draw.circle(self.image, eye_color, (w - 15 if self.dir > 0 else 15, h // 2), eye_size)
        self.mask = pygame.mask.from_surface(self.image)
        self._since_attack = 0
        self.x_vel = 0
        self.y_vel = 0
        self.direction_timer = 0
        self.direction_change_interval = random.uniform(0.5, 5.0)

    def update(self, dt, objects=None, player=None):
        """Monster with patrolling behavior and collision avoidance."""
        self._since_attack += dt
        self.direction_timer += dt

        # Change direction randomly every 0.5-5 seconds
        if self.direction_timer >= self.direction_change_interval:
            self.dir = random.choice([-1, 1])
            self.direction_timer = 0
            self.direction_change_interval = random.uniform(0.5, 5.0)

        # Check for collision with sprites above
        if objects:
            for obj in objects:
                if obj.rect.colliderect(self.rect) and obj.rect.bottom == self.rect.top:
                    # Teleport 10 pixels up if colliding with sprite above
                    self.rect.y -= 10
                    break

        # Check if about to fall off platform
        falling = True
        if objects:
            for obj in objects:
                if (obj.rect.left <= self.rect.centerx <= obj.rect.right and
                    obj.rect.top >= self.rect.bottom and
                    obj.rect.top - self.rect.bottom <= 20):  # Check within 20 pixels below
                    falling = False
                    break

        if falling:
            # Change direction to avoid falling
            self.dir *= -1

        # Set horizontal velocity based on direction
        self.x_vel = self.dir * self.SPEED * 0.5  # Slower patrolling speed
        self.y_vel = 0  # No vertical movement unless falling

        # Move
        self.rect.x += int(self.x_vel * dt * FPS / 60)
        self.rect.y += int(self.y_vel * dt * FPS / 60)

        # Update the monster's appearance based on direction
        w, h = self.rect.width, self.rect.height
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(self.image, self.COLOR, (0, 0, w, h))
        # Draw "eye" to show direction
        eye_color = (255, 255, 0)
        eye_size = 8
        pygame.draw.circle(self.image, eye_color, (w - 15 if self.dir > 0 else 15, h // 2), eye_size)

    def draw(self, window, offset_x=0, offset_y=0):
        """Draw the monster on the window with camera offset."""
        window.blit(self.image, (self.rect.x - offset_x, self.rect.y - offset_y))
        
    def can_attack(self):
        """Check if monster can attack again."""
        return self._since_attack >= 0  # Can always attack

class Boss(Monster):
    """Stronger enemy with enhanced abilities."""
    COLOR = (150, 0, 0)  # Red color
    DEFAULT_SIZE = (80, 80)  # Larger size
    SPEED = PLAYER_VEL * 1.5  # 1.5x player speed
    DAMAGE = 15.0  # More damage
    CHASE_RANGE = 800  # Large detection range
    HP = 10  # 10 HP

    def __init__(self, x, y, w=None, h=None):
        super().__init__(x, y, w or self.DEFAULT_SIZE[0], h or self.DEFAULT_SIZE[1])
        self.health = self.HP
        self.max_health = self.HP

    def update(self, dt, objects=None, player=None):
        """Boss AI - enhanced movement."""
        self._since_attack += dt

        if player:
            # Always chase player
            dist_x = player.rect.centerx - self.rect.centerx
            dist_y = player.rect.centery - self.rect.centery
            total_dist = (dist_x**2 + dist_y**2) ** 0.5
            
            if total_dist > 0:
                # Calculate direction vector to player
                dir_x = dist_x / total_dist
                dir_y = dist_y / total_dist
                
                # Set velocity directly toward player
                self.x_vel = dir_x * self.SPEED
                self.y_vel = dir_y * self.SPEED
                
                # Update direction for sprite facing
                if dist_x > 0:
                    self.dir = 1  # Face right
                elif dist_x < 0:
                    self.dir = -1  # Face left
            else:
                # If directly on player, keep moving
                self.x_vel = self.dir * self.SPEED
                self.y_vel = 0
            
            # Move
            self.rect.x += int(self.x_vel * dt * FPS / 60)
            self.rect.y += int(self.y_vel * dt * FPS / 60)
            
            # Update the monster's appearance based on direction
            w, h = self.rect.width, self.rect.height
            self.image = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(self.image, self.COLOR, (0, 0, w, h))
            # Draw "eye" to show direction
            eye_color = (255, 255, 0)
            eye_size = 12  # Larger eye for boss
            pygame.draw.circle(self.image, eye_color, (w - 20 if self.dir > 0 else 20, h // 2), eye_size)