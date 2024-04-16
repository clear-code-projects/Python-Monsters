from settings import *
from game_data import *
from pytmx.util_pygame import load_pygame
from os.path import join
from random import randint

from sprites import Sprite, AnimatedSprite, MonsterPatchSprite, BorderSprite, CollidableSprite, TransitionSprite
from entities import Player, Character
from groups import AllSprites
from dialog import DialogTree
from monster_index import MonsterIndex
from battle import Battle
from timer import Timer
from evolution import Evolution

from support import *
from monster import Monster

class Game:
	# general 
	def __init__(self):
		pygame.init()
		self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
		pygame.display.set_caption('Monster Hunter')
		self.clock = pygame.time.Clock()
		self.encounter_timer = Timer(2000, func = self.monster_encounter)

		# player monsters 
		self.player_monsters = {
			0: Monster('Ivieron', 32),
			1: Monster('Atrox', 15),
			2: Monster('Cindrill', 16),
			3: Monster('Atrox', 10),
			4: Monster('Sparchu', 11),
			5: Monster('Gulfin', 9),
			6: Monster('Jacana', 10),
		}
		for monster in self.player_monsters.values():
			monster.xp += randint(0,monster.level * 100)
		self.test_monsters = {
			0: Monster('Finsta', 15),
			1: Monster('Pouch', 13),
			2: Monster('Larvea', 12),
		}


		# groups 
		self.all_sprites = AllSprites()
		self.collision_sprites = pygame.sprite.Group()
		self.character_sprites = pygame.sprite.Group()
		self.transition_sprites = pygame.sprite.Group()
		self.monster_sprites = pygame.sprite.Group()

		# transition / tint
		self.transition_target = None
		self.tint_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
		self.tint_mode = 'untint'
		self.tint_progress = 0
		self.tint_direction = -1
		self.tint_speed = 600

		self.import_assets()
		self.setup(self.tmx_maps['world'], 'house')
		self.audio['overworld'].play(-1)

		# overlays 
		self.dialog_tree = None
		self.monster_index = MonsterIndex(self.player_monsters, self.fonts, self.monster_frames)
		self.index_open = False
		self.battle = None
		self.evolution = None


	def import_assets(self):
		self.tmx_maps = tmx_importer('..', 'data', 'maps')

		self.overworld_frames = {
			'water': import_folder('..', 'graphics', 'tilesets', 'water'),
			'coast': coast_importer(24, 12, '..', 'graphics', 'tilesets', 'coast'),
			'characters': all_character_import('..', 'graphics', 'characters')
		}

		self.monster_frames = {
			'icons': import_folder_dict('..', 'graphics', 'icons'),
			'monsters': monster_importer(4,2,'..', 'graphics', 'monsters'),
			'ui': import_folder_dict('..', 'graphics', 'ui'),
			'attacks': attack_importer('..', 'graphics', 'attacks')
		}
		self.monster_frames['outlines'] = outline_creator(self.monster_frames['monsters'], 4)

		self.fonts = {
			'dialog': pygame.font.Font(join('..', 'graphics', 'fonts', 'PixeloidSans.ttf'), 30),
			'regular': pygame.font.Font(join('..', 'graphics', 'fonts', 'PixeloidSans.ttf'), 18),
			'small': pygame.font.Font(join('..', 'graphics', 'fonts', 'PixeloidSans.ttf'), 14),
			'bold': pygame.font.Font(join('..', 'graphics', 'fonts', 'dogicapixelbold.otf'), 20),
		}
		self.bg_frames = import_folder_dict('..', 'graphics', 'backgrounds')
		self.start_animation_frames = import_folder('..', 'graphics', 'other', 'star animation')
	
		self.audio = audio_importer('..', 'audio')

	def setup(self, tmx_map, player_start_pos):
		# clear the map
		for group in (self.all_sprites, self.collision_sprites, self.transition_sprites, self.character_sprites):
			group.empty()

		# terrain
		for layer in ['Terrain', 'Terrain Top']:
			for x, y, surf in tmx_map.get_layer_by_name(layer).tiles():
				Sprite((x * TILE_SIZE, y * TILE_SIZE), surf, self.all_sprites, WORLD_LAYERS['bg'])

		# water 
		for obj in tmx_map.get_layer_by_name('Water'):
			for x in range(int(obj.x), int(obj.x + obj.width), TILE_SIZE):
				for y in range(int(obj.y), int(obj.y + obj.height), TILE_SIZE):
					AnimatedSprite((x,y), self.overworld_frames['water'], self.all_sprites, WORLD_LAYERS['water'])

		# coast
		for obj in tmx_map.get_layer_by_name('Coast'):
			terrain = obj.properties['terrain']
			side = obj.properties['side']
			AnimatedSprite((obj.x, obj.y), self.overworld_frames['coast'][terrain][side], self.all_sprites, WORLD_LAYERS['bg'])
		
		# objects 
		for obj in tmx_map.get_layer_by_name('Objects'):
			if obj.name == 'top':
				Sprite((obj.x, obj.y), obj.image, self.all_sprites, WORLD_LAYERS['top'])
			else:
				CollidableSprite((obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites))

		# transition objects
		for obj in tmx_map.get_layer_by_name('Transition'):
			TransitionSprite((obj.x, obj.y), (obj.width, obj.height), (obj.properties['target'], obj.properties['pos']), self.transition_sprites)

		# collision objects 
		for obj in tmx_map.get_layer_by_name('Collisions'):
			BorderSprite((obj.x, obj.y), pygame.Surface((obj.width, obj.height)), self.collision_sprites)

		# grass patches 
		for obj in tmx_map.get_layer_by_name('Monsters'):
			MonsterPatchSprite((obj.x, obj.y), obj.image, (self.all_sprites, self.monster_sprites), obj.properties['biome'], obj.properties['monsters'], obj.properties['level'])

		# entities 
		for obj in tmx_map.get_layer_by_name('Entities'):
			if obj.name == 'Player':
				if obj.properties['pos'] == player_start_pos:
					self.player = Player(
						pos = (obj.x, obj.y), 
						frames = self.overworld_frames['characters']['player'], 
						groups = self.all_sprites,
						facing_direction = obj.properties['direction'], 
						collision_sprites = self.collision_sprites)
			else:
				Character(
					pos = (obj.x, obj.y), 
					frames = self.overworld_frames['characters'][obj.properties['graphic']], 
					groups = (self.all_sprites, self.collision_sprites, self.character_sprites),
					facing_direction = obj.properties['direction'],
					character_data = TRAINER_DATA[obj.properties['character_id']],
					player = self.player,
					create_dialog = self.create_dialog,
					collision_sprites = self.collision_sprites,
					radius = obj.properties['radius'],
					nurse = obj.properties['character_id'] == 'Nurse',
					notice_sound = self.audio['notice'])

	# dialog system
	def input(self):
		if not self.dialog_tree and not self.battle:
			keys = pygame.key.get_just_pressed()
			if keys[pygame.K_SPACE]:
				for character in self.character_sprites:
					if check_connections(100, self.player, character):
						self.player.block()
						character.change_facing_direction(self.player.rect.center)
						self.create_dialog(character)
						character.can_rotate = False

			if keys[pygame.K_RETURN]:
				self.index_open = not self.index_open
				self.player.blocked = not self.player.blocked

	def create_dialog(self, character):
		if not self.dialog_tree:
			self.dialog_tree = DialogTree(character, self.player, self.all_sprites, self.fonts['dialog'], self.end_dialog)

	def end_dialog(self, character):
		self.dialog_tree = None
		if character.nurse:
			for monster in self.player_monsters.values():
				monster.health = monster.get_stat('max_health')
				monster.energy = monster.get_stat('max_energy')

			self.player.unblock()
		elif not character.character_data['defeated']:
			self.audio['overworld'].stop()
			self.audio['battle'].play(-1)
			self.transition_target = Battle(
				player_monsters = self.player_monsters, 
				opponent_monsters = character.monsters, 
				monster_frames = self.monster_frames, 
				bg_surf = self.bg_frames[character.character_data['biome']], 
				fonts = self.fonts, 
				end_battle = self.end_battle,
				character = character, 
				sounds = self.audio)
			self.tint_mode = 'tint'
		else:
			self.player.unblock()
			self.check_evolution()

	# transition system
	def transition_check(self):
		sprites = [sprite for sprite in self.transition_sprites if sprite.rect.colliderect(self.player.hitbox)]
		if sprites:
			self.player.block()
			self.transition_target = sprites[0].target
			self.tint_mode = 'tint'

	def tint_screen(self, dt):
		if self.tint_mode == 'untint':
			self.tint_progress -= self.tint_speed * dt

		if self.tint_mode == 'tint':
			self.tint_progress += self.tint_speed * dt
			if self.tint_progress >= 255:
				if type(self.transition_target) == Battle:
					self.battle = self.transition_target
				elif self.transition_target == 'level':
					self.battle = None
				else:
					self.setup(self.tmx_maps[self.transition_target[0]], self.transition_target[1])
				self.tint_mode = 'untint'
				self.transition_target = None

		self.tint_progress = max(0, min(self.tint_progress, 255))
		self.tint_surf.set_alpha(self.tint_progress)
		self.display_surface.blit(self.tint_surf, (0,0))
	
	def end_battle(self, character):
		self.audio['battle'].stop()
		self.transition_target = 'level'
		self.tint_mode = 'tint'
		if character:
			character.character_data['defeated'] = True
			self.create_dialog(character)
		elif not self.evolution:
			self.player.unblock()
			self.check_evolution()

	def check_evolution(self):
		for index, monster in self.player_monsters.items():
			if monster.evolution:
				if monster.level == monster.evolution[1]:
					self.audio['evolution'].play()
					self.player.block()
					self.evolution = Evolution(self.monster_frames['monsters'], monster.name, monster.evolution[0], self.fonts['bold'], self.end_evolution, self.start_animation_frames)
					self.player_monsters[index] = Monster(monster.evolution[0], monster.level)
		if not self.evolution:
			self.audio['overworld'].play(-1)

	def end_evolution(self):
		self.evolution = None
		self.player.unblock()
		self.audio['evolution'].stop()
		self.audio['overworld'].play(-1)

	# monster encounters 
	def check_monster(self):
		if [sprite for sprite in self.monster_sprites if sprite.rect.colliderect(self.player.hitbox)] and not self.battle and self.player.direction:
			if not self.encounter_timer.active:
				self.encounter_timer.activate()

	def monster_encounter(self):
		sprites = [sprite for sprite in self.monster_sprites if sprite.rect.colliderect(self.player.hitbox)]
		if sprites and self.player.direction:
			self.encounter_timer.duration = randint(800, 2500)
			self.player.block()
			self.audio['overworld'].stop()
			self.audio['battle'].play(-1)
			self.transition_target = Battle(
				player_monsters = self.player_monsters, 
				opponent_monsters = {index:Monster(monster, sprites[0].level + randint(-3,3)) for index, monster in enumerate(sprites[0].monsters)}, 
				monster_frames = self.monster_frames, 
				bg_surf = self.bg_frames[sprites[0].biome], 
				fonts = self.fonts, 
				end_battle = self.end_battle,
				character = None, 
				sounds = self.audio)
			self.tint_mode = 'tint'

	def run(self):
		while True:
			dt = self.clock.tick() / 1000
			self.display_surface.fill('black')

			# event loop 
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					pygame.quit()
					exit()

			# update 
			self.encounter_timer.update()
			self.input()
			self.transition_check()
			self.all_sprites.update(dt)
			self.check_monster()
			
			# drawing
			self.all_sprites.draw(self.player)
			
			# overlays 
			if self.dialog_tree: self.dialog_tree.update()
			if self.index_open:  self.monster_index.update(dt)
			if self.battle:      self.battle.update(dt)
			if self.evolution:   self.evolution.update(dt)

			self.tint_screen(dt)
			pygame.display.update()

if __name__ == '__main__':
	game = Game()
	game.run()