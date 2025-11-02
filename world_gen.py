import random
from player import Block

class WorldGenerator:
    def __init__(self, block_size):
        self.block_size = block_size
        self.seed = 42
        random.seed(self.seed)
        
        # my-style level parameters
        self.ground_height = 3  # blocks high for ground
        self.section_width = 20  # Wider sections for more variety
        self.generated_sections = set()
        
    def generate_section(self, section_index, ground_y):
        """Generate one section of my-style level."""
        if section_index in self.generated_sections:
            return []
        
        self.generated_sections.add(section_index)
        blocks = []
        
        # Deterministic random for this section
        section_random = random.Random(hash((section_index, self.seed)))
        start_x = section_index * self.section_width * self.block_size
        
        # NO ground blocks - only platforms!
        
        # Generate varied platform patterns with multiple routes
        pattern = section_random.choice(['multi_route', 'high_low', 'spiral', 'choice_path', 
                                        'vertical_maze', 'wave', 'split_merge', 'layered'])
        
        if pattern == 'multi_route':
            # Three parallel routes at different heights
            for route in range(3):
                route_y = ground_y - (route + 2) * self.block_size * 2
                num_platforms = section_random.randint(3, 5)
                for i in range(num_platforms):
                    x = start_x + i * self.block_size * 4
                    length = section_random.randint(4, 8)  # Increased platform length
                    for j in range(length):
                        blocks.append(Block(x + j * self.block_size, route_y, self.block_size))
                        
        elif pattern == 'high_low':
            # Alternating high and low platforms
            for i in range(8):
                x = start_x + i * self.block_size * 2.5
                if i % 2 == 0:
                    y = ground_y - self.block_size * 2
                else:
                    y = ground_y - self.block_size * 6
                length = section_random.randint(4, 6)  # Increased platform length
                for j in range(length):
                    blocks.append(Block(int(x) + j * self.block_size, int(y), self.block_size))
                    
        elif pattern == 'spiral':
            # Spiral upward pattern
            for i in range(10):
                x = start_x + (i % 5) * self.block_size * 3
                y = ground_y - (i // 2) * self.block_size * 2
                for j in range(4):  # Increased from 2 to 4
                    blocks.append(Block(x + j * self.block_size, y, self.block_size))
                    
        elif pattern == 'choice_path':
            # Fork in the road - player chooses high or low path
            # Lower path
            for i in range(5):
                x = start_x + (i + 2) * self.block_size * 2
                y = ground_y - self.block_size * 2
                # Increased platform width from 2 to 4 blocks
                for j in range(4):
                    blocks.append(Block(x + j * self.block_size, y, self.block_size))
            
            # Upper path
            for i in range(5):
                x = start_x + (i + 2) * self.block_size * 2
                y = ground_y - self.block_size * 7
                # Increased platform width from 2 to 4 blocks
                for j in range(4):
                    blocks.append(Block(x + j * self.block_size, y, self.block_size))
                
        elif pattern == 'vertical_maze':
            # Vertical platforms requiring precise jumping
            for i in range(6):
                x = start_x + i * self.block_size * 3
                y = ground_y - section_random.randint(2, 8) * self.block_size
                # Make platforms wider (3 blocks instead of 1)
                for j in range(3):
                    blocks.append(Block(x + j * self.block_size, y, self.block_size))
                # Add a second platform nearby for variety
                if section_random.random() > 0.5:
                    for j in range(3):
                        blocks.append(Block(x + j * self.block_size, y - self.block_size * 2, self.block_size))
                    
        elif pattern == 'wave':
            # Smooth wave pattern going up and down
            for i in range(12):
                x = start_x + i * self.block_size * 1.5
                # Sine wave for height
                height_offset = int(3 * (1 + section_random.random() * 0.5) * 
                                  (1 if (i // 3) % 2 == 0 else -1))
                y = ground_y - self.block_size * (4 + height_offset)
                # Make platforms wider (3 blocks instead of 1)
                for j in range(3):
                    blocks.append(Block(int(x) + j * self.block_size, y, self.block_size))
                
        elif pattern == 'split_merge':
            # Paths split then merge back
            # Main path
            for i in range(4):
                x = start_x + i * self.block_size * 2
                y = ground_y - self.block_size * 3
                # Make platforms wider (3 blocks instead of 1)
                for j in range(3):
                    blocks.append(Block(x + j * self.block_size, y, self.block_size))
            
            # Split paths
            for i in range(4, 8):
                x = start_x + i * self.block_size * 2
                # Upper branch - make wider
                for j in range(3):
                    blocks.append(Block(x + j * self.block_size, ground_y - self.block_size * 6, self.block_size))
                # Lower branch - make wider
                for j in range(3):
                    blocks.append(Block(x + j * self.block_size, ground_y - self.block_size * 1, self.block_size))
            
            # Merge back
            for i in range(8, 12):
                x = start_x + i * self.block_size * 2
                y = ground_y - self.block_size * 3
                # Make platforms wider (3 blocks instead of 1)
                for j in range(3):
                    blocks.append(Block(x + j * self.block_size, y, self.block_size))
                
        elif pattern == 'layered':
            # Multiple layers with connections
            layers = [
                ground_y - self.block_size * 2,
                ground_y - self.block_size * 5,
                ground_y - self.block_size * 8
            ]
            
            for layer_y in layers:
                # Platforms on each layer
                num_plat = section_random.randint(3, 5)
                for i in range(num_plat):
                    x = start_x + i * self.block_size * 3
                    length = section_random.randint(4, 6)  # Increased platform length
                    for j in range(length):
                        blocks.append(Block(x + j * self.block_size, layer_y, self.block_size))
        
        # Add connecting blocks between routes for extra mobility (make them wider)
        for _ in range(section_random.randint(3, 6)):
            x = start_x + section_random.randint(1, 18) * self.block_size
            y = ground_y - section_random.randint(3, 10) * self.block_size
            # Make connecting blocks wider (3 blocks instead of 1)
            for j in range(3):
                blocks.append(Block(x + j * self.block_size, y, self.block_size))
        
        # Add high platforms for advanced routes
        for _ in range(section_random.randint(2, 4)):
            x = start_x + section_random.randint(2, 16) * self.block_size
            y = ground_y - section_random.randint(9, 14) * self.block_size
            length = section_random.randint(2, 4)
            for j in range(length):
                blocks.append(Block(x + j * self.block_size, y, self.block_size))
        
        return blocks
    
    def generate_region(self, min_x, max_x, ground_y):
        """Generate all sections in a horizontal range."""
        blocks = []
        
        # Convert to section indices
        start_section = min_x // (self.section_width * self.block_size)
        end_section = (max_x // (self.section_width * self.block_size)) + 1
        
        for section_idx in range(start_section, end_section):
            section_blocks = self.generate_section(section_idx, ground_y)
            blocks.extend(section_blocks)
        
        return blocks
    
    def cleanup_far_sections(self, player_x, cleanup_distance):
        """Remove sections that are too far from player."""
        player_section = player_x // (self.section_width * self.block_size)
        cleanup_sections = player_section - cleanup_distance // (self.section_width * self.block_size)
        
        sections_to_remove = [s for s in self.generated_sections if s < cleanup_sections]
        for s in sections_to_remove:
            self.generated_sections.discard(s)