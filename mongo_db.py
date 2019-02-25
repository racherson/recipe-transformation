import pymongo as pm

# establish connection with localhost and given port number, used to communicate with running database instance
client = pm.MongoClient('localhost', 27017)

# access database, if no database with the given name exists, it will create one when saving data to it
# db = client['recipe_transform']

# specify which collection (table) to use
# recipes = db.recipes

# example of inserting data
# recipe_1 = {
#     'name': 'Szechuan Chicken',
#     'ingredients': 'Lots of spice',
#     'cuisine': 'Chinese'
# }
# recipe_2 = {
#     'name': 'Carbonara Pasta',
#     'ingredients': 'Pasta, cream, bacon',
#     'cuisine': 'Italian'
# }
# one_result = recipes.insert_one(recipe_1)
# print('One recipe: {0}'.format(one_result.inserted_id))
# many_result = recipes.insert_many([recipe_1, recipe_2])
# print('Multiple recipes: {0}'.format(many_result.inserted_ids))

# example of retrieving data
# an_italian_recipe = recipes.find_one({'cuisine': 'Italian'})
# print(an_italian_recipe)
# chinese_recipes = recipes.find({'cuisine': 'Chinese'})
# print(chinese_recipes)
# for recipe in chinese_recipes:
#     print(recipe)
