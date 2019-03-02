# EECS 337 Project 2
# Recipe Transformer


# healthy substitutions
healthy = {}


# if sugar: cut in half, make other half cinnamon, cloves, or nutmeg, or stevia
class Ingredient:
    def __init__(self, name, adjective, amount, unit):
        self.name = name
        self.adjective = adjective
        self.amount = amount
        self.unit = unit

    def remove(self):
        pass


def add_ingredient(name, adjective, amount, unit):
    Ingredient(name, adjective, amount, unit)


# loop through every ingredient.name in the recipe:
ingredient_list = []


for ingredient in ingredient_list:
    if (ingredient.name == "butter" and ingredient.adjective != "peanut") or ingredient.name == "shortening" or ingredient.name == "oil":
        ingredient.amount = ingredient.amount / 2
        add_ingredient("applesauce", "unsweetened", ingredient.amount, ingredient.unit)
    if ingredient.name == "sugar":
        ingredient.name = "stevia"
    if ingredient.name == "salt":
        ingredient.adjective = "himalayan"
    if ingredient.name == "pasta":
        ingredient.adjective = "whole-wheat"
    if ingredient.name == "milk":
        ingredient.adjective = "almond"
    if ingredient.type == "topping":
        ingredient.remove()
    if ingredient.name == "cheese":
        ingredient.amount = ingredient.amount / 2
    if ingredient.type == "condiment":
        if ingredient.name == "jelly" or ingredient.name == "jam":
            ingredient.name = ingredient.adjective
        ingredient.remove()
    if ingredient.name == "egg":
        ingredient.adjective = "substitute"
        ingredient.amount = ingredient.amount / 4
        ingredient.unit = "cup"
    if ingredient.type == "vegetable":
        ingredient.amount = ingredient.amount * 2
    if ingredient.name == "rice":
        ingredient.name = "quinoa"
    if ingredient.name == "cream" and ingredient.adjective == "sour":
        ingredient.name = "yogurt"
        ingredient.adjective = "greek"
    if ingredient.name == "flour":
        ingredient.adjective = "whole-wheat"
    if ingredient.name == "chocolate":
        ingredient.name = "nibs"
        ingredient.adjective = "cocoa"
    if ingredient.adjective == "iceberg":
        ingredient.adjective = "romaine"
    if ingredient.adjective == "peanut":
        ingredient.adjective = "almond"
