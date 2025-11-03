import pygame
import sys
import settings
from settings import WIDTH, HEIGHT, FPS, BLOCK_SIZE, HEALTH_REGEN_RATE, STAMINA_REGEN_RATE, MANA_REGEN_RATE
from player import Player, Block, Object, handle_move, handle_ledge_grab
from gui import draw, get_background, UI, spawn_monsters_on_surfaces
from monster import Boss
from world_gen import WorldGenerator

pygame.init()
pygame.display.set_caption("my-style Platformer")
window = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))

def validate_classes():
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
        raise ImportError(f"Required class(es) not found: {', '.join(missing)}")

def reset_game():
    """Reset game state for respawn."""
    objects = []
    monsters = []
    
    # Starting platform only (no ground)
    starting_platform_y = settings.HEIGHT - BLOCK_SIZE * 4
    
    # Create small starting platform
    for i in range(5):
        objects.append(Block(i * BLOCK_SIZE, starting_platform_y, BLOCK_SIZE))
    
    player = Player(100, starting_platform_y - 60, 50, 50)
    player.x_vel = 0
    player.y_vel = 0
    
    ui = UI(player, objects)
    
    world_gen = WorldGenerator(BLOCK_SIZE)
    
    # Generate large initial world with all platforms
    print("Generating world platforms...")
    initial_blocks = world_gen.generate_region(-WIDTH * 2, WIDTH * 20, starting_platform_y)
    objects.extend(initial_blocks)
    print(f"Generated {len(initial_blocks)} platform blocks")
    
    # Spawn initial monsters on all available blocks
    available_blocks = [o for o in objects if isinstance(o, Block)]
    if available_blocks:
        initial_monster_count = min(15, len(available_blocks) // 10)
        initial_monsters = spawn_monsters_on_surfaces(
            available_blocks, 
            num_monsters=initial_monster_count, 
            monster_size=(40, 40)
        )
        monsters_list = initial_monsters
        print(f"Spawned {len(initial_monsters)} initial monsters")
    else:
        monsters_list = []
    
    return player, objects, monsters_list, ui, world_gen, starting_platform_y

def draw_death_screen(window):
    """Draw death screen with respawn button."""
    overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT))
    overlay.fill((0, 0, 0))
    overlay.set_alpha(128)
    window.blit(overlay, (0, 0))
    
    font = pygame.font.Font(None, 74)
    text = font.render("You Died", True, (255, 0, 0))
    text_rect = text.get_rect(center=(settings.WIDTH//2, settings.HEIGHT//2 - 50))
    
    button_font = pygame.font.Font(None, 36)
    button_text = button_font.render("Respawn", True, (255, 255, 255))
    button_rect = pygame.Rect(0, 0, 200, 50)
    button_rect.center = (settings.WIDTH//2, settings.HEIGHT//2 + 50)
    
    window.blit(text, text_rect)
    # Make button more visible with a brighter color
    pygame.draw.rect(window, (150, 150, 150), button_rect)
    # Add a border to make it more clickable-looking
    pygame.draw.rect(window, (200, 200, 200), button_rect, 2)
    window.blit(button_text, button_text.get_rect(center=button_rect.center))
    
    return button_rect

def main():
    global window
    validate_classes()

    clock = pygame.time.Clock()
    background, bg_image = get_background("Blue.png")
    initial_w, initial_h = settings.WIDTH, settings.HEIGHT

    # Game state
    player, objects, monsters, ui, world_gen, starting_y = reset_game()
    
    # Monster spawning
    MONSTER_SPAWN_INTERVAL = 5.0
    MAX_MONSTERS = 20
    monster_spawn_timer = 0.0
    
    # Boss timer (3 minutes)
    BOSS_TIMER = 180.0
    boss_countdown = BOSS_TIMER
    boss_spawned = False
    arena_bounds = None
    
    # Camera
    camera_x = 0
    camera_y = 0
    
    # Death system - far below starting position
    DEATH_LINE_Y = starting_y + BLOCK_SIZE * 15
    is_dead = False
    respawn_button = None
    
    # Generation tracking
    last_gen_right = settings.WIDTH * 2
    GENERATE_AHEAD = settings.WIDTH * 2
    
    run = True
    fixed_dt = 1.0 / settings.FPS
    
    # Pre-render timer font and surface to prevent flickering
    timer_font = pygame.font.Font(None, 48)
    last_timer_text = ""
    timer_text_surface = None

    while run:
        clock.tick(settings.FPS)
        dt = fixed_dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break
                
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Player attack - instantly kill monsters on left click
                if not is_dead and not ui.inventory_open and not ui.options_open:
                    mouse_pos = pygame.mouse.get_pos()
                    # Check if any monster was clicked
                    monsters_to_remove = []
                    for m in monsters:
                        if m.rect.collidepoint(mouse_pos):
                            monsters_to_remove.append(m)
                    
                    # Remove killed monsters
                    for m in monsters_to_remove:
                        monsters.remove(m)
                
                if is_dead and respawn_button and respawn_button.collidepoint(event.pos):
                    player, objects, monsters, ui, world_gen, starting_y = reset_game()
                    is_dead = False
                    boss_spawned = False
                    boss_countdown = BOSS_TIMER
                    arena_bounds = None
                    monster_spawn_timer = 0.0
                    DEATH_LINE_Y = starting_y + BLOCK_SIZE * 15
                    continue
                    
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
                    player.dash()
                elif event.key == pygame.K_e:
                    player.stomp()

        if not is_dead:
            # Regeneration
            ui.health = min(ui.max_health, ui.health + HEALTH_REGEN_RATE * dt)
            ui.stamina = min(ui.max_stamina, ui.stamina + STAMINA_REGEN_RATE * dt)
            ui.mana = min(ui.max_mana, ui.mana + MANA_REGEN_RATE * dt)

            # Update player physics
            player.loop(settings.FPS, dt)

            # Handle stomp collisions after physics update
            if player.stomping:
                collided_blocks = []
                for obj in objects[:]:
                    if pygame.sprite.collide_mask(player, obj) and isinstance(obj, Block):
                        collided_blocks.append(obj)
                for obj in collided_blocks:
                    objects.remove(obj)

                monsters_to_remove = []
                for m in monsters[:]:
                    if pygame.sprite.collide_mask(player, m):
                        monsters_to_remove.append(m)
                for m in monsters_to_remove:
                    monsters.remove(m)

                if collided_blocks or monsters_to_remove:
                    player.y_vel = -player.GRAVITY * 12  # Even higher bounce jump
                    player.stomping = False
                    player.stomp_timer = 0.0
                    player.stomp_cooldown_timer = 0.0

            handle_move(player, objects)
            handle_ledge_grab(player, objects, dt, BLOCK_SIZE)

            # Camera follows player both horizontally and vertically
            player_x = player.rect.centerx
            player_y = player.rect.centery
            
            target_camera_x = int(player_x - settings.WIDTH // 2)
            target_camera_y = int(player_y - settings.HEIGHT // 2)
            
            # Smooth camera following
            camera_x += (target_camera_x - camera_x) * 0.15
            camera_y += (target_camera_y - camera_y) * 0.15

            # Generate new sections ahead of player if needed
            if player_x + GENERATE_AHEAD > last_gen_right:
                new_blocks = world_gen.generate_region(
                    last_gen_right,
                    last_gen_right + settings.WIDTH * 5,
                    starting_y
                )
                objects.extend(new_blocks)
                last_gen_right += settings.WIDTH * 5
                
                # Spawn monsters on new blocks
                if new_blocks and len(monsters) < MAX_MONSTERS:
                    new_monsters = spawn_monsters_on_surfaces(new_blocks, num_monsters=5, monster_size=(40, 40))
                    monsters.extend(new_monsters)

            # Cleanup far objects
            cleanup_x = player_x - settings.WIDTH * 3
            for obj in objects[:]:
                if isinstance(obj, Block) and obj.rect.x < cleanup_x:
                    if obj in objects:
                        objects.remove(obj)

            # Monster spawning on platforms
            monster_spawn_timer += dt
            if monster_spawn_timer >= MONSTER_SPAWN_INTERVAL and not boss_spawned:
                monster_spawn_timer = 0.0
                if len(monsters) < MAX_MONSTERS:
                    # Find blocks near player for spawning
                    blocks_near = [o for o in objects if isinstance(o, Block) 
                                 and abs(o.rect.centerx - player_x) < settings.WIDTH * 3]
                    
                    if blocks_near:
                        # Filter out blocks that already have monsters
                        def block_has_monster(b):
                            for m in monsters:
                                if (m.rect.bottom == b.rect.top and 
                                    abs(m.rect.centerx - b.rect.centerx) <= b.rect.width // 2):
                                    return True
                            return False
                        
                        available_blocks = [b for b in blocks_near if not block_has_monster(b)]
                        if available_blocks:
                            to_spawn = min(5, MAX_MONSTERS - len(monsters))
                            new_monsters = spawn_monsters_on_surfaces(
                                available_blocks, 
                                num_monsters=to_spawn,
                                monster_size=(40, 40)
                            )
                            monsters.extend(new_monsters)

            # Update monsters
            for m in monsters[:]:
                m.update(dt, objects, player)
                
                # Check if monster fell off world
                if m.rect.y > DEATH_LINE_Y:
                    monsters.remove(m)
                    continue
                
                # Apply damage when monster touches player
                if m.rect.colliderect(player.rect):
                    damage_dealt = m.DAMAGE * dt
                    ui.health = max(0.0, ui.health - damage_dealt)
                    # Trigger damage flash
                    ui.damage_flash = min(1.0, ui.damage_flash + 0.3)

            # Boss countdown
            if not boss_spawned:
                boss_countdown -= dt
                if boss_countdown <= 0:
                    # Create arena at current position
                    arena_width = int(settings.WIDTH * 2)
                    left_bound = player_x - arena_width // 4
                    right_bound = left_bound + arena_width

                    # Clear existing monsters
                    monsters.clear()

                    # Create arena walls
                    left_wall = Object(left_bound - 48, -settings.HEIGHT * 2, 
                                     48, settings.HEIGHT * 6, name="ArenaWall")
                    right_wall = Object(right_bound, -settings.HEIGHT * 2, 
                                      48, settings.HEIGHT * 6, name="ArenaWall")
                    
                    for wall in (left_wall, right_wall):
                        wall.image.fill((255, 0, 0))
                        wall.mask = pygame.mask.from_surface(wall.image)
                        objects.append(wall)

                    # Spawn boss in center of arena
                    boss = Boss(left_bound + arena_width // 2, starting_y - 100)
                    monsters.append(boss)
                    boss_spawned = True
                    arena_bounds = (left_bound, right_bound)

            # Check for death
            if player.rect.bottom > DEATH_LINE_Y or ui.health <= 0:
                is_dead = True

            # Update minimap with monsters
            ui.update_minimap(player, objects, int(camera_x), int(camera_y), monsters)

            # Draw world
            draw(window, background, bg_image, player, objects, camera_x, ui,
                 monsters=monsters, camera_y=camera_y)

            # Draw boss countdown without flickering
            if not boss_spawned:
                timer_str = f"Boss: {int(boss_countdown) // 60:02d}:{int(boss_countdown) % 60:02d}"
                # Only re-render if text changed
                if timer_str != last_timer_text:
                    timer_text_surface = timer_font.render(timer_str, True, (255, 0, 0))
                    last_timer_text = timer_str
                
                if timer_text_surface:
                    window.blit(timer_text_surface, 
                              (settings.WIDTH // 2 - timer_text_surface.get_width() // 2, 20))

        else:
            # Death screen
            draw(window, background, bg_image, player, objects, camera_x, ui,
                 monsters=monsters, camera_y=camera_y)
            respawn_button = draw_death_screen(window)

        pygame.display.update()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()