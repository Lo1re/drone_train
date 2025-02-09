import pygame
import cv2
import subprocess 

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

def start_game():
    pygame.quit()
    subprocess.run(["python", "game.py"])  
    exit()

def calibrate():
    pygame.quit()
    subprocess.run(["python", "calibration.py"])
    exit()

def change_background():
    global game_background
    game_background = "new_background.jpg"  
    print("Фон гри змінено")

def quit_game():
    pygame.quit()
    exit()

pygame.init()
screen = pygame.display.set_mode((1280, 720))
pygame.display.set_caption("Меню")
menu_background = pygame.image.load("D:/jammer/myGame/images/menu_background.jpg")
menu_background = pygame.transform.scale(menu_background, (1280, 720))

game_background = "background2.jpg"  
running = True
while running:
    screen.blit(menu_background, (0, 0))
    draw_button(screen, "Старт", 490, 250, 300, 60, (0, 0, 255), (0, 0, 200), start_game)
    draw_button(screen, "Калібрування", 490, 350, 300, 60, (255, 255, 0), (200, 200, 0), calibrate)
    draw_button(screen, "Змінити фон", 490, 450, 300, 60, (0, 150, 255), (0, 100, 200), change_background)
    draw_button(screen, "Вихід", 490, 550, 300, 60, (255, 0, 0), (200, 0, 0), quit_game)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    pygame.display.update()

pygame.quit()
exit()