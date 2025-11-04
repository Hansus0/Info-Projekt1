import pygame
import sys
import settings
from settings import WIDTH, HEIGHT, FPS, BLOCK_SIZE, HEALTH_REGEN_RATE, STAMINA_REGEN_RATE, MANA_REGEN_RATE
from player import Player, Block, Object, handle_move, handle_ledge_grab
from gui import draw, get_background, UI, spawn_monsters_on_surfaces
from monster import Monster, Boss  # 🟩 Monster zusätzlich importiert
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
    
    # 🟩 Spawn monsters directly using Monster.spawn_on_platform
    available_blocks = [o for o in objects if isinstance(o, Block)]
    if available_blocks:
        initial_monster_count = min(15, len(available_blocks) // 10)
        monsters_list = [
            Monster(*Monster.spawn_on_platform(available_blocks)) for _ in range(initial_monster_count)
        ]
        print(f"Spawned {len(monsters_list)} initial monsters")
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
    pygame.draw.rect(window, (150, 150, 150), button_rect)
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
                    monsters_to_remove = [m for m in monsters if m.rect.collidepoint(mouse_pos)]
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

            player.loop(settings.FPS, dt)

            # Handle stomp
            if player.stomping:
                collided_blocks = [o for o in objects if pygame.sprite.collide_mask(player, o) and isinstance(o, Block)]
                for obj in collided_blocks:
                    objects.remove(obj)

                monsters_to_remove = [m for m in monsters if pygame.sprite.collide_mask(player, m)]
                for m in monsters_to_remove:
                    monsters.remove(m)

                if collided_blocks or monsters_to_remove:
                    player.y_vel = -player.GRAVITY * 12
                    player.stomping = False
                    player.stomp_timer = 0.0
                    player.stomp_cooldown_timer = 0.0

            handle_move(player, objects)
            handle_ledge_grab(player, objects, dt, BLOCK_SIZE)

            player_x = player.rect.centerx
            player_y = player.rect.centery
            
            target_camera_x = int(player_x - settings.WIDTH // 2)
            target_camera_y = int(player_y - settings.HEIGHT // 2)
            
            camera_x += (target_camera_x - camera_x) * 0.15
            camera_y += (target_camera_y - camera_y) * 0.15

            # World generation (unchanged)
            if player_x + GENERATE_AHEAD > last_gen_right:
                new_blocks = world_gen.generate_region(
                    last_gen_right,
                    last_gen_right + settings.WIDTH * 5,
                    starting_y
                )
                objects.extend(new_blocks)
                last_gen_right += settings.WIDTH * 5
                
                # 🟩 Optional: spawn with Monster.spawn_on_platform
                if new_blocks and len(monsters) < MAX_MONSTERS:
                    for _ in range(5):
                        x, y = Monster.spawn_on_platform(new_blocks)
                        monsters.append(Monster(x, y))

            # 🟩 Update monsters (neue Signatur & Attack)
            for m in monsters[:]:
                platforms = [o for o in objects if isinstance(o, Block)]
                m.update(dt, platforms, player)
                m.attack_player(player, dt)  # 🟩 Schaden über Monster-Logik
                
                if m.rect.y > DEATH_LINE_Y:
                    monsters.remove(m)
                    continue

            # Boss countdown bleibt unverändert
            if not boss_spawned:
                boss_countdown -= dt
                if boss_countdown <= 0:
                    arena_width = int(settings.WIDTH * 2)
                    left_bound = player_x - arena_width // 4
                    right_bound = left_bound + arena_width
                    monsters.clear()
                    left_wall = Object(left_bound - 48, -settings.HEIGHT * 2, 48, settings.HEIGHT * 6, name="ArenaWall")
                    right_wall = Object(right_bound, -settings.HEIGHT * 2, 48, settings.HEIGHT * 6, name="ArenaWall")
                    for wall in (left_wall, right_wall):
                        wall.image.fill((255, 0, 0))
                        wall.mask = pygame.mask.from_surface(wall.image)
                        objects.append(wall)
                    boss = Boss(left_bound + arena_width // 2, starting_y - 100)
                    monsters.append(boss)
                    boss_spawned = True
                    arena_bounds = (left_bound, right_bound)

            if player.rect.bottom > DEATH_LINE_Y or ui.health <= 0:
                is_dead = True

            ui.update_minimap(player, objects, int(camera_x), int(camera_y), monsters)
            draw(window, background, bg_image, player, objects, camera_x, ui,
                 monsters=monsters, camera_y=camera_y)

            if not boss_spawned:
                timer_str = f"Boss: {int(boss_countdown) // 60:02d}:{int(boss_countdown) % 60:02d}"
                if timer_str != last_timer_text:
                    timer_text_surface = timer_font.render(timer_str, True, (255, 0, 0))
                    last_timer_text = timer_str
                if timer_text_surface:
                    window.blit(timer_text_surface, 
                              (settings.WIDTH // 2 - timer_text_surface.get_width() // 2, 20))

        else:
            draw(window, background, bg_image, player, objects, camera_x, ui,
                 monsters=monsters, camera_y=camera_y)
            respawn_button = draw_death_screen(window)

        pygame.display.update()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()