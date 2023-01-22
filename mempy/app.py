import datetime
import os

from flask import Flask, render_template, redirect, request

from pymongo import MongoClient
from bson import ObjectId

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

language_key = os.environ.get("LANGUAGE_KEY")
language_endpoint = os.environ.get("LANGUAGE_ENDPOINT")

credential = AzureKeyCredential(language_key)
azure_client = TextAnalyticsClient(endpoint=language_endpoint, credential=credential)

app = Flask(__name__)

client = MongoClient(os.environ.get("COSMOS_DB_CONNECTION_STRING"))
db = client.blog 

@app.route("/") 
def index():
    posts = db.posts.find({})
    return render_template("index.html", posts=posts)

@app.route("/blog/new", methods=["GET", "POST"])
def blog_new():
    if request.method == "GET":
        return render_template("blog_new.html")
    else:
        author = request.form["author"]
        title = request.form["title"]
        body = request.form["body"]
        db.posts.insert_one({"author": author, "title": title, "body": body, "created": datetime.datetime.now(), "comments": []})
        return redirect("/")

@app.route("/blog/detail/<post_id>", methods=["GET", "POST"])
def blog_detail(post_id):
    if request.method == "GET":
        post = db.posts.find_one({"_id": ObjectId(post_id)})
        pos_avg = 0
        neg_avg = 0
        neu_avg = 0
        if len(post["comments"]) > 0:
            for comment in post["comments"]:
                pos_avg += comment["positive"]
                neg_avg += comment["negative"]
                neu_avg += comment["neutral"]
            pos_avg /= len(post["comments"])
            neg_avg /= len(post["comments"])
            neu_avg /= len(post["comments"])
        return render_template("blog_detail.html", post=post, avgs=(pos_avg, neg_avg, neu_avg))
    else:
        comment_body = request.form["body"]
        sentiment = azure_client.analyze_sentiment([comment_body])[0]
        new_comment = {"body": comment_body, "positive": sentiment.confidence_scores.positive, "negative": sentiment.confidence_scores.negative, "neutral": sentiment.confidence_scores.neutral}
        db.posts.update_one({"_id": ObjectId(post_id)}, {"$push": {"comments": new_comment}})
        return redirect(f"/blog/detail/{post_id}")