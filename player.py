class Player(pygame.sprite.Sprite):
	# ... alle bisherigen Konstanten bleiben gleich ...

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

		# 🟩 Lebenspunkte hinzufügen
		self.max_health = 100
		self.health = self.max_health
		self.invincible_time = 0.0   # kleine Immunität nach Schaden

		# Ledge, Dash, Stomp usw. bleiben unverändert
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

	# 🟩 Neue Methode: Schaden erhalten
	def take_damage(self, amount):
		"""Reduce player health by amount, trigger hit flash."""
		if self.invincible_time > 0.0:
			return  # temporär unverwundbar
		self.health -= amount
		self.hit = True
		self.hit_count = 0
		self.invincible_time = 0.5  # halbe Sekunde Immunität nach Treffer
		if self.health <= 0:
			self.health = 0

	# 🟩 Lebensregeneration oder Tod prüfen (optional)
	def is_dead(self):
		return self.health <= 0

	def heal(self, amount):
		self.health = min(self.max_health, self.health + amount)

	def loop(self, fps, dt):
		# 🟩 Immunitäts-Timer updaten
		if self.invincible_time > 0.0:
			self.invincible_time = max(0.0, self.invincible_time - dt)

		# --- ab hier bleibt die originale loop()-Logik ---
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
