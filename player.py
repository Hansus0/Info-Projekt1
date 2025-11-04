class Player(pygame.sprite.Sprite):
    DASH_SPEED = 900.0
    DASH_DURATION = 0.18
    DASH_COOLDOWN = 1.5
    STOMP_GRAVITY_MULTIPLIER = 8.0
    STOMP_DURATION = 0.3
    STOMP_COOLDOWN = 1.0
    COLOR = (255, 0, 0)
    GRAVITY = 1
    SPRITES = {}
    ANIMATION_DELAY = 3
    HOLD_MAX = 10.0

    def __init__(self, x, y, width, height):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.x_vel = 0
        self.y_vel = 0
        self.mask = None
        self.direction = "left"
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0

        # 🟩 Lebenspunkte
        self.max_health = 100
        self.health = self.max_health
        self.invincible_time = 0.0

        # Ledge, Dash, Stomp usw.
        self.holding = False
        self.hold_time = 0.0
        self.hold_block = None
        self.hold_side = None
        self.hold_regrab_cooldown = 0.0

        self.dash_timer = 0.0
        self.dash_cooldown_timer = self.DASH_COOLDOWN
        self.dashing = False
        self.dash_dir = 0
        self.dash_speed = self.DASH_SPEED

        self.stomp_timer = 0.0
        self.stomp_cooldown_timer = self.STOMP_COOLDOWN
        self.stomping = False

        self.ensure_sprites_loaded()
        try:
            self.sprite = self.SPRITES["idle_left"][0]
            self.update()
        except Exception:
            self.sprite = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.rect(self.sprite, self.COLOR, (0,0,width,height))
            self.update()

    # 🟩 Neue Methoden für Gesundheit
    def take_damage(self, amount):
        """Reduziere Lebenspunkte, trigger Immunität/Hit-Flash."""
        if self.invincible_time > 0.0:
            return
        self.health -= amount
        self.hit = True
        self.hit_count = 0
        self.invincible_time = 0.5  # 0.5 Sekunden Immunität nach Treffer
        if self.health <= 0:
            self.health = 0

    def is_dead(self):
        return self.health <= 0

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    # --- Loop/Update ---
    def loop(self, fps, dt):
        # 🟩 Update Immunitäts-Timer
        if self.invincible_time > 0.0:
            self.invincible_time = max(0.0, self.invincible_time - dt)

        if getattr(self, "hold_regrab_cooldown", 0.0) > 0.0:
            self.hold_regrab_cooldown = max(0.0, self.hold_regrab_cooldown - dt)

        self.dash_cooldown_timer = min(self.DASH_COOLDOWN, self.dash_cooldown_timer + dt)
        self.stomp_cooldown_timer = min(self.STOMP_COOLDOWN, self.stomp_cooldown_timer + dt)

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

        if self.dashing:
            dx = int(self.dash_dir * self.dash_speed * dt)
            if dx != 0:
                self.move(dx, 0)
            self.dash_timer = max(0.0, self.dash_timer - dt)
            if self.dash_timer <= 0.0:
                self.dashing = False
                self.x_vel = 0
            self.update_sprite()
            return

        if self.stomping:
            self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY * self.STOMP_GRAVITY_MULTIPLIER)
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

        self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
        self.move(self.x_vel, self.y_vel)
        if self.hit:
            self.hit_count += 1
        if self.hit_count > fps * 2:
            self.hit = False
            self.hit_count = 0
        self.fall_count += 1
        self.update_sprite()

    # --- Sprite / Movement ---
    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    def jump(self):
        self.y_vel = -self.GRAVITY * 8
        self.animation_count = 0
        self.jump_count += 1
        if self.jump_count == 1:
            self.fall_count = 0

    def dash(self):
        if self.dash_cooldown_timer >= self.DASH_COOLDOWN and not self.holding:
            self.dashing = True
            self.dash_timer = self.DASH_DURATION
            self.dash_cooldown_timer = 0.0
            self.dash_dir = -1 if self.direction == "left" else 1
            self.x_vel = 0
            return True
        return False

    def stomp(self):
        if self.stomp_cooldown_timer >= self.STOMP_COOLDOWN and not self.holding and not self.dashing:
            self.stomping = True
            self.stomp_timer = self.STOMP_DURATION
            self.stomp_cooldown_timer = 0.0
            return True
        return False

    def landed(self):
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0

    def hit_head(self):
        self.y_vel *= -1

    def update_sprite(self):
        sprite_sheet = "idle"
        if self.hit:
            sprite_sheet = "hit"
        elif self.y_vel < 0:
            sprite_sheet = "jump" if self.jump_count == 1 else "double_jump"
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
            pass
        self.animation_count += 1
        self.update()

    def update(self):
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win, offset_x):
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))

    @classmethod
    def ensure_sprites_loaded(cls):
        if cls.SPRITES:
            return
        try:
            if pygame.display.get_surface() is None:
                return
        except Exception:
            return
        try:
            cls.SPRITES = load_sprite_sheets("MainCharacter", "", 32, 32, True)
        except Exception:
            cls.SPRITES = {}