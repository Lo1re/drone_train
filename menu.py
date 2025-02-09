import pygame
import cv2
import subprocess
import tkinter as tk
from tkinter import filedialog

class DropDown():
    def __init__(self, color_menu, color_option, x, y, w, h, font, main, options):
        self.color_menu = color_menu
        self.color_option = color_option
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.main = main
        self.options = options
        self.draw_menu = False
        self.menu_active = False
        self.active_option = -1

    def draw(self, surf):
        pygame.draw.rect(surf, self.color_menu[self.menu_active], self.rect, 0)
        msg = self.font.render(self.main, 1, (0, 0, 0))
        surf.blit(msg, msg.get_rect(center = self.rect.center))

        if self.draw_menu:
            for i, text in enumerate(self.options):
                rect = self.rect.copy()
                rect.y += (i+1) * self.rect.height
                pygame.draw.rect(surf, self.color_option[1 if i == self.active_option else 0], rect, 0)
                msg = self.font.render(text, 1, (0, 0, 0))
                surf.blit(msg, msg.get_rect(center = rect.center))

    def update(self, event_list):
        mpos = pygame.mouse.get_pos()
        self.menu_active = self.rect.collidepoint(mpos)
        
        self.active_option = -1
        for i in range(len(self.options)):
            rect = self.rect.copy()
            rect.y += (i+1) * self.rect.height
            if rect.collidepoint(mpos):
                self.active_option = i
                break

        if not self.menu_active and self.active_option == -1:
            self.draw_menu = False

        for event in event_list:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.menu_active:
                    self.draw_menu = not self.draw_menu
                elif self.draw_menu and self.active_option >= 0:
                    self.draw_menu = False
                    return self.active_option
        return -1

def draw_button(screen, text, x, y, width, height, color, hover_color, action=None):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    
    if x < mouse[0] < x + width and y < mouse[1] < y + height:
        pygame.draw.rect(screen, hover_color, (x, y, width, height))
        if click[0] == 1 and action is not None:
            action()
    else:
        pygame.draw.rect(screen, color, (x, y, width, height))
    
    font = pygame.font.Font(None, 36)
    text_surface = font.render(text, True, (0, 0, 0))
    text_rect = text_surface.get_rect(center=(x + width // 2, y + height // 2))
    screen.blit(text_surface, text_rect)

def draw_text(screen, text, x, y, color=(255, 255, 255)):
    font = pygame.font.Font(None, 36)
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))

def start_game():
    # Save settings to file
    with open("game_settings.txt", "w") as f:
        f.write(f"{difficulty_level}\n{num_drones}")
    
    pygame.quit()
    subprocess.run(["python", "game.py"])
    exit()

def calibrate():
    pygame.quit()
    subprocess.run(["python", "calibration.py"])
    exit()

def change_background():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.png")])
    if file_path:
        with open("background_config.txt", "w") as f:
            f.write(file_path)
        print("Фон гри змінено на", file_path)

def quit_game():
    pygame.quit()
    exit()

pygame.init()
screen = pygame.display.set_mode((1280, 720))
pygame.display.set_caption("Меню")
menu_background = pygame.image.load("D:/jammer/myGame/images/menu_background.jpg")
menu_background = pygame.transform.scale(menu_background, (1280, 720))

# Налаштування шрифту та кольорів для випадаючих списків
COLOR_INACTIVE = (100, 200, 255)
COLOR_ACTIVE = (0, 150, 255)
COLOR_LIST_INACTIVE = (200, 200, 200)
COLOR_LIST_ACTIVE = (150, 150, 150)

font = pygame.font.Font(None, 32)

# Створення випадаючих списків
list_difficulty = DropDown(
    [COLOR_INACTIVE, COLOR_ACTIVE],
    [COLOR_LIST_INACTIVE, COLOR_LIST_ACTIVE],
    490, 250, 300, 40, 
    font,
    "Виберіть рівень складності",
    ["Легкий (повільний дрон)", 
     "Середній (швидкий дрон)", 
     "Складний (багато дронів)"]
)

# Перемістили список дронів вліво
list_drones = DropDown(
    [COLOR_INACTIVE, COLOR_ACTIVE],
    [COLOR_LIST_INACTIVE, COLOR_LIST_ACTIVE],
    160, 250, 300, 40,  # Нова позиція X=160 замість 490
    font,
    "Виберіть кількість дронів",
    ["1", "2", "3", "4", "5"]
)

difficulty_level = 1
num_drones = 1

running = True
while running:
    event_list = pygame.event.get()
    for event in event_list:
        if event.type == pygame.QUIT:
            running = False

    screen.blit(menu_background, (0, 0))
    
    # Оновлення та відображення випадаючих списків
    selected_difficulty = list_difficulty.update(event_list)
    if selected_difficulty >= 0:
        difficulty_level = selected_difficulty + 1
        list_difficulty.main = list_difficulty.options[selected_difficulty]

    selected_drones = list_drones.update(event_list)
    if selected_drones >= 0:
        num_drones = selected_drones + 1
        list_drones.main = list_drones.options[selected_drones]

    # Додаємо текст-підказку для вибору кількості дронів
    if difficulty_level == 3:
        draw_text(screen, "Кількість дронів:", 160, 220)
        list_drones.draw(screen)

    list_difficulty.draw(screen)
    
    # Малювання кнопок
    draw_button(screen, "Старт", 490, 400, 300, 60, (0, 0, 255), (0, 0, 200), start_game)
    draw_button(screen, "Калібрування", 490, 480, 300, 60, (255, 255, 0), (200, 200, 0), calibrate)
    draw_button(screen, "Змінити фон", 490, 560, 300, 60, (0, 150, 255), (0, 100, 200), change_background)
    draw_button(screen, "Вихід", 490, 640, 300, 60, (255, 0, 0), (200, 0, 0), quit_game)
    
    pygame.display.flip()

pygame.quit()
exit()