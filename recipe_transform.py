# EECS 337 Project 2
# Recipe Transformer
import urllib.request

url = input("Please provide a recipe url ")
page = urllib.request.urlopen(url)
print(page.read())
