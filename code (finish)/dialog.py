from settings import * 
from timer import Timer

class DialogTree:
	def __init__(self, character, player, all_sprites, font, end_dialog):
		self.player = player
		self.character = character
		self.font = font 
		self.all_sprites = all_sprites
		self.end_dialog = end_dialog
		
		self.dialog = character.get_dialog()
		self.dialog_num = len(self.dialog)
		self.dialog_index = 0

		self.current_dialog = DialogSprite(self.dialog[self.dialog_index], self.character, self.all_sprites, self.font)
		self.dialog_timer = Timer(500, autostart = True)

	def input(self):
		keys = pygame.key.get_just_pressed()
		if keys[pygame.K_SPACE] and not self.dialog_timer.active:
			self.current_dialog.kill()
			self.dialog_index += 1
			if self.dialog_index < self.dialog_num:
				self.current_dialog = DialogSprite(self.dialog[self.dialog_index], self.character, self.all_sprites, self.font)
				self.dialog_timer.activate()
			else:
				self.end_dialog(self.character)

	def update(self):
		self.dialog_timer.update()
		self.input()

class DialogSprite(pygame.sprite.Sprite):
	def __init__(self, message, character, groups, font):
		super().__init__(groups)
		self.z = WORLD_LAYERS['top']

		# text 
		text_surf = font.render(message, False, COLORS['black'])
		padding = 5
		width = max(30, text_surf.get_width() + padding * 2)
		height = text_surf.get_height() + padding * 2

		# background
		surf = pygame.Surface((width, height), pygame.SRCALPHA)
		surf.fill((0,0,0,0))
		pygame.draw.rect(surf, COLORS['pure white'], surf.get_frect(topleft = (0,0)),0, 4)
		surf.blit(text_surf, text_surf.get_frect(center = (width / 2, height / 2)))

		self.image = surf
		self.rect = self.image.get_frect(midbottom = character.rect.midtop + vector(0,-10))