from flask import Flask
import pymongo
from bson.json_util import dumps
from flask import request
import requests
import re
from datetime import datetime
import base64
from PIL import Image
import io
import json


def set_image(file):
    # Reduce the size of the image
    img = Image.open(file.stream).convert('RGB')

    img = img.resize((img.width // 5, img.height // 5))
    # Convert the image to a Base64-encoded string
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return encoded_string


app = Flask(__name__)

client = pymongo.MongoClient("mongodb://localhost:27017/")
DB = client["fyp-news-dataset"]
COLLECTION = DB["news-dataset"]
USER_COLLECTION = DB["user-dataset"]


def remove_special_chars(string):
    # Define the pattern to match special characters but not full stops
    pattern = r'[^a-zA-z0-9\s\.]'

    # Use regex to substitute special characters with empty string
    return re.sub(pattern, '', string)


@app.route("/get/news")
def get_news():
    news = COLLECTION.find({})
    return dumps(news)


# create a news post with title, content, date, location, approved, tags, category and image in form data with unique id
@app.route("/create/news", methods=['POST'])
def create_news():
    title = request.form.get('title')
    content = request.form.get('content')

    # Current data and time in ISO format
    date = datetime.now().isoformat()


    # get the location from the ip address
    ip = request.remote_addr
    url = "http://ip-api.com/json/"
    response = requests.request("GET", url)
    response = response.json()
    location = response["city"] + ", " + response["country"]


    tags = request.form.get('tags')
    category = request.form.get('category')

    news_id = COLLECTION.count_documents({}) + 1
    

    image = request.files['image']
    image = set_image(image)
    aadhar_image = request.files['aadhar_image']
    aadhar_image = set_image(aadhar_image)

    content = remove_special_chars(content)

    # remove the news lines and punctuation marks from the content
    content = content.replace("\n", " ")
    content = content.replace("\r", " ")
    print(content)
    


    url = "http://127.0.0.1:5001/api/fake-news-detection/"
    headers = {
        'Content-Type': 'text/plain'
    }
    response = requests.request("POST", url, headers=headers, data=content)

    # return the response in json format
    response = response.json()

    approved = response["data"]

    if title == "" or content == "" or location == "" or approved == "" or tags == "" or category == "" or image == "" or aadhar_image == "":
        return dumps({"error": "Please fill all the fields"})



    news = COLLECTION.insert_one(
        {
        "news_id" : news_id,
        'title': title,
        'content': content,
        'date': date,
        'location': location,
        'approved': approved,
        'tags': tags,
        'category': category, 
        'image': image,
        'aadhar_image': aadhar_image
        })

    # jsonify the response and return it
    return ({"success": "News created successfully"})

# get the news by id
@app.route("/get/news/<id>")
def get_news_by_id(id):
    # convert the id to int
    id = int(id)
    news = COLLECTION.find_one({"news_id": id})

    # return the news in json format
    return dumps(news)

# get the news by category
@app.route("/get/news/category/<category>")
def get_news_by_category(category):
    # get the news from the database
    news = COLLECTION.find({"category": category})

    # return the news in json format
    return dumps(news)

# Login with username and password and save the token in the database
@app.route("/api/login", methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == "" or password == "":
        return dumps({"error": "Please fill all the fields"})

    # get the user from the database
    user = USER_COLLECTION.find_one({"username": username})

    if user is None:
        return dumps({"error": "Username does not exist"})

    if user["password"] != password:
        return dumps({"error": "Password is incorrect"})

    # generate a token
    token = USER_COLLECTION.count_documents({}) + 1

    # save the token in the database
    USER_COLLECTION.update_one({"username": username}, {"$set": {"token": token}})

    return dumps({"message": "Login Success"})

# Register function 
@app.route("/api/register", methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == "" or password == "":
        return dumps({"error": "Please fill all the fields"})
    
    # check if the username already exists
    user = USER_COLLECTION.find_one({"username": username})

    if user is not None:
        return dumps({"error": "Username already exists"})
    
    # save the user in the database
    user = USER_COLLECTION.insert_one(
        {
        'username': username,
        'password': password
        })
    
    return dumps({"success": "User created successfully"})

# get the news with short content
@app.route("/get/news/short")
def get_news_short():
    url = "http://127.0.0.1:5002/api/text-summerization-model/"
    headers = {
        'Content-Type': 'application/json'
    }

    content = json.dumps({
        "rawData" : request.form.get('content')
    })

    response = requests.request("POST", url, headers=headers, data=content)

    # return the response in json format
    response = response.json()

    data = response["data"]

    print(data)
    return dumps({
        "real" : request.form.get('content'),
        "short" : data
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1',port=8000,debug=True)