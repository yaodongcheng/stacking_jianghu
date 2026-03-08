# --- src/entities/resource.py ---
import pygame
from src.definitions import *
from .base import CardBase

class Resource(CardBase):
    def __init__(self, x, y, item_type, count=1):
        super().__init__(x, y, CARD_W, CARD_H, COLOR_RESOURCE_CARD)
        self.card_type = CARD_TYPE_RESOURCE
        self.item_type = item_type
        self.name = item_type # 例如 "木材", "粮"
        self.count = count
        
        
        self.color = (100, 180, 100) # 默认绿
       

    def draw(self, screen, font):
        if self.count > 1:
            showName = f"{self.name}x{self.count}"
        else:
            showName = self.name
        super().draw_card_bg(screen, font,showName)
        