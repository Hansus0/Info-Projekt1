import pygame
import sys
import settings
from settings import WIDTH, HEIGHT, FPS, BLOCK_SIZE, HEALTH_REGEN_RATE, STAMINA_REGEN_RATE, MANA_REGEN_RATE
from player import Player, Block, Object, handle_move, handle_ledge_grab
from gui import draw, get_background, UI, update_ground, generate_cubes, spawn_monsters_on_surfaces
from monster import Boss  # Add Boss import
from world_gen import WorldGenerator

pygame.init()
pygame.display.set_caption("Platformer")
# use settings.WIDTH/HEIGHT so we can update them at runtime
window = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))

def validate_classes():
	"""
	Simple runtime validation: ensure key classes exist and are types.
	Raises ImportError with a short message if something is missing.
	"""
	required = {
		"Player": Player,
		"Block": Block,
		"Object": Object,
		"UI": UI,
	}
	missing = []
	for name, obj in required.items():
		if obj is None or not isinstance(obj, type):
			missing.append(name)
	if missing:
		raise ImportError(f"Required class(es) not found or not a class: {', '.join(missing)}. Ensure modules define these classes.")

def main():
    global window
    # validate that required classes are present and correct before running
    validate_classes()

    clock = pygame.time.Clock()
    background, bg_image = get_background("Blue.png")
    block_size = BLOCK_SIZE
    ground_y = settings.HEIGHT - block_size

    # store initial windowed size so we can restore after fullscreen
    initial_w, initial_h = settings.WIDTH, settings.HEIGHT

    # player original spawn
    player_spawn_x = 100
    player_spawn_y = 100
    player = Player(player_spawn_x, player_spawn_y, 50, 50)

    # create initial floor
    floor = [Block(i * block_size, ground_y, block_size)
             for i in range(-settings.WIDTH // block_size, (settings.WIDTH * 2) // block_size)]
    objects = [*floor, Block(0, settings.HEIGHT - block_size * 2, block_size),
               Block(block_size * 3, settings.HEIGHT - block_size * 4, block_size),]

    # --- add invisible wall just to the left of original spawn so player cannot cross left ---
    # Move left wall to screen edge
    wall_x = 0  # screen edge instead of relative to player
    wall_width = 48
    wall_height = settings.HEIGHT * 6  # tall enough to block above/below camera
    wall_y = -settings.HEIGHT * 2     # position so it spans vertically through world
    left_wall = Object(wall_x, wall_y, wall_width, wall_height, name="InvisibleWall")
    # make collision solid (opaque mask) but keep it invisible by flag
    left_wall.image.fill((255,255,255,255))  # opaque for mask
    left_wall.mask = pygame.mask.from_surface(left_wall.image)
    left_wall.invisible = True
    objects.append(left_wall)

    ui = UI(player, objects)
    occupied = set((obj.rect.x, obj.rect.y) for obj in objects if isinstance(obj, Block))

    # spawn monsters on any surface
    monsters = spawn_monsters_on_surfaces(objects, num_monsters=4, monster_size=(40,40))

    # --- procedurally generate platforms to the right of the player original spawn ---
    right_gen_min = player_spawn_x + 200
    right_gen_max = player_spawn_x + settings.WIDTH * 3
    extra_platforms = generate_cubes(right_gen_min, right_gen_max, 24, block_size, occupied, ground_y, player.rect, max_vertical_gap=block_size * 4)
    if extra_platforms:
        objects.extend(extra_platforms)
        for p in extra_platforms:
            occupied.add((p.rect.x, p.rect.y))

    # Initialize procedural-generation state (cubes etc.) and perform initial generation
    cubes = []
    CUBE_BATCH = 8
    GENERATE_CHUNK = settings.WIDTH * 2
    offset_x = 0

    start_gen = offset_x - GENERATE_CHUNK
    end_gen = offset_x + settings.WIDTH + GENERATE_CHUNK
    initial_batch = CUBE_BATCH * 3
    initial_cubes = generate_cubes(start_gen, end_gen, initial_batch, block_size, occupied, ground_y, player.rect, max_vertical_gap=block_size * 4)
    if initial_cubes:
        cubes.extend(initial_cubes)
        objects.extend(initial_cubes)
        for p in initial_cubes:
            occupied.add((p.rect.x, p.rect.y))

    # set generation cursors to the edges of the initial generated region
    # center generation on player's current position so spawning follows the player
    player_x = player.rect.centerx
    next_gen_right = player_x + GENERATE_CHUNK
    next_gen_left = player_x - GENERATE_CHUNK

    # monster respawn controls (ensure defined before use)
    MONSTER_SPAWN_INTERVAL = 3.0   # spawn more frequently
    MAX_MONSTERS = 12              # allow more monsters
    monster_spawn_timer = 0.0

    # Initialize vertical generation state with simpler tracking
    VERTICAL_STEP = block_size * 4
    last_gen_height = ground_y

    # Add boss timer and state
    BOSS_TIMER = 180.0  # 3 minutes in seconds
    boss_countdown = BOSS_TIMER
    boss_spawned = False
    boss = None
    arena_bounds = None

    # Replace procedural generation with deterministic world generator
    world_gen = WorldGenerator(block_size)
    
    # Generate initial ground (first 100m)
    ground_blocks = [Block(i * block_size, ground_y, block_size)
                    for i in range(100)]
    objects.extend(ground_blocks)

    # Generate initial visible area plus buffer
    visible_blocks = world_gen.generate_region(
        0, settings.WIDTH * 2,  # horizontal range
        -settings.HEIGHT * 2, settings.HEIGHT * 2  # vertical range
    )
    objects.extend(visible_blocks)

    # Track camera bounds for generation
    last_gen_right = settings.WIDTH * 2
    last_gen_top = -settings.HEIGHT * 2
    last_gen_bottom = settings.HEIGHT * 2

    run = True
    # fixed physics timestep (1 / FPS) to keep physics consistent across display modes
    fixed_dt = 1.0 / settings.FPS

    while run:
        ms = clock.tick(settings.FPS)
        # force physics updates to fixed timestep so movement is independent of real ms variations
        dt = fixed_dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break
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
                    if action:
                        if "set_resolution" in action:
                            new_w, new_h = action["set_resolution"]
                            settings.WIDTH, settings.HEIGHT = new_w, new_h
                            flags = pygame.FULLSCREEN | pygame.SCALED if ui.fullscreen else 0
                            window = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT), flags)
                            background, bg_image = get_background("Blue.png")
                        if "toggle_fullscreen" in action:
                            ui.fullscreen = action["toggle_fullscreen"]
                            if ui.fullscreen:
                                info = pygame.display.Info()
                                settings.WIDTH, settings.HEIGHT = info.current_w, info.current_h
                                window = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
                            else:
                                settings.WIDTH, settings.HEIGHT = initial_w, initial_h
                                window = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))
                            background, bg_image = get_background("Blue.png")
                    continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_i:
                    ui.toggle_inventory()
                elif event.key == pygame.K_o:
                    ui.toggle_options()
                elif event.key == pygame.K_TAB and ui.inventory_open:
                    ui.cycle_tab()
                elif event.key == pygame.K_SPACE and player.jump_count < 2 and not player.holding:
                    player.jump()
                elif event.key == pygame.K_q:
                    # dash when Q pressed
                    player.dash()

        # regen then clamp using dt (fixed timestep)
        ui.health = min(ui.max_health, ui.health + HEALTH_REGEN_RATE * dt)
        ui.stamina = min(ui.max_stamina, ui.stamina + STAMINA_REGEN_RATE * dt)
        ui.mana = min(ui.max_mana, ui.mana + MANA_REGEN_RATE * dt)

        # update physics with consistent FPS value
        player.loop(settings.FPS, dt)
        handle_move(player, objects)
        handle_ledge_grab(player, objects, dt, block_size)

        # recompute player world x and camera offset each frame
        player_x = player.rect.centerx
        update_ground(objects, block_size, offset_x, ground_y)

        # Remove monsters whose supporting block has been removed
        for m in monsters[:]:
            supported = False
            for o in objects:
                if isinstance(o, Block) and m.rect.bottom == o.rect.top and abs(m.rect.centerx - o.rect.centerx) <= (o.rect.width // 2):
                    supported = True
                    break
            if not supported:
                monsters.remove(m)

        # cleanup off-screen cubes but allow generation to continue
        remove_margin = settings.WIDTH
        for c in cubes[:]:
            if arena_bounds and (c.rect.x < arena_bounds[0] or c.rect.x > arena_bounds[1]):
                # Remove cubes outside arena after boss spawn
                if c in objects:
                    objects.remove(c)
                cubes.remove(c)
                occupied.discard((c.rect.x, c.rect.y))
            elif not arena_bounds and (c.rect.x < player_x - remove_margin or c.rect.x > player_x + settings.WIDTH + remove_margin):
                # Normal cleanup before boss
                if c in objects:
                    objects.remove(c)
                cubes.remove(c)
                occupied.discard((c.rect.x, c.rect.y))

        # Generate new platforms above if player is climbing
        if player.rect.y < last_gen_height:
            new_height = last_gen_height - VERTICAL_STEP
            new_cubes = generate_cubes(
                player_x - settings.WIDTH,
                player_x + settings.WIDTH,
                CUBE_BATCH,
                block_size,
                occupied,
                new_height,
                player.rect
            )
            if new_cubes:
                cubes.extend(new_cubes)
                objects.extend(new_cubes)
                for p in new_cubes:
                    occupied.add((p.rect.x, p.rect.y))
                last_gen_height = new_height

        # Auto-spawn monsters periodically on available surfaces (avoid stacking monsters)
        monster_spawn_timer += dt
        if monster_spawn_timer >= MONSTER_SPAWN_INTERVAL:
            monster_spawn_timer = 0.0
            if len(monsters) < MAX_MONSTERS:
                # candidate blocks: any Block that doesn't already have a monster on top
                blocks = [o for o in objects if isinstance(o, Block)]
                def block_has_mon(b):
                    for mm in monsters:
                        if mm.rect.bottom == b.rect.top and abs(mm.rect.centerx - b.rect.centerx) <= (b.rect.width // 2):
                            return True
                    return False
                candidates = [b for b in blocks if not block_has_mon(b)]
                if candidates:
                    to_spawn = min(MAX_MONSTERS - len(monsters), max(1, len(candidates)//4))
                    new_mons = spawn_monsters_on_surfaces(candidates, num_monsters=to_spawn, monster_size=(40,40))
                    monsters.extend(new_mons)

        # Boss timer and spawn logic
        if not boss_spawned:
            boss_countdown -= dt
            if boss_countdown <= 0:
                # Create arena bounds (1.5x screen width)
                arena_width = int(settings.WIDTH * 1.5)
                left_bound = player.rect.centerx - arena_width // 2
                right_bound = left_bound + arena_width

                # Create visible red walls
                left_arena_wall = Object(left_bound, -settings.HEIGHT * 2, 48, settings.HEIGHT * 6, name="ArenaWall")
                right_arena_wall = Object(right_bound, -settings.HEIGHT * 2, 48, settings.HEIGHT * 6, name="ArenaWall")
                for wall in (left_arena_wall, right_arena_wall):
                    wall.image.fill((255, 0, 0))  # Red color
                    wall.mask = pygame.mask.from_surface(wall.image)
                    objects.append(wall)

                # Spawn boss in arena
                boss = Boss(left_bound + arena_width // 2, ground_y - 100)
                monsters.append(boss)
                boss_spawned = True
                arena_bounds = (left_bound, right_bound)

        # Draw countdown if boss not spawned
        if not boss_spawned:
            font = pygame.font.Font(None, 36)
            minutes = int(boss_countdown) // 60
            seconds = int(boss_countdown) % 60
            timer_text = font.render(f"{minutes:02d}:{seconds:02d}", True, (255, 0, 0))
            window.blit(timer_text, (settings.WIDTH - 100, 20))

        # Update camera position to follow player both horizontally and vertically
        camera_x = int(player.rect.centerx - settings.WIDTH // 2)
        camera_y = int(player.rect.centery - settings.HEIGHT // 2)

        # Draw world with camera offsets
        draw(window, background, bg_image, player, objects, camera_x, ui, 
             monsters=monsters, camera_y=camera_y)

        # Update monsters and apply damage
        for m in monsters:
            m.update(dt, objects, player)
            if m.rect.inflate(14, 14).colliderect(player.rect):
                # Apply monster's damage rate scaled by dt
                ui.health = max(0.0, ui.health - (m.DAMAGE * dt))

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()