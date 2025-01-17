# import the necessary packages
from flask import Flask, render_template, redirect, url_for, request, session, Response
from werkzeug.utils import secure_filename
import sqlite3
import pandas as pd
from datetime import datetime
import os

# from AskGemini import *
from chatgptTest import *
from YT_Download import *
from audio_transcribe import *
from nlp import *
from deepmultilingualpunctuation import PunctuationModel
from moviepy import VideoFileClip

import speech_recognition as sr

from splitAudio import split_audio

r = sr.Recognizer()
model = PunctuationModel()

name = ""
paragraph = ""

app = Flask(__name__)

app.secret_key = "1234"
app.config["CACHE_TYPE"] = "null"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.route("/", methods=["GET", "POST"])
def landing():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    global name
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        con = sqlite3.connect("mydatabase.db")
        cursorObj = con.cursor()
        cursorObj.execute(
            f"SELECT Name from Users WHERE Email='{email}' AND password = '{password}';"
        )
        try:
            name = cursorObj.fetchone()[0]
            return redirect(url_for("image"))
        except:
            error = "Invalid Credentials Please try again..!!!"
            return render_template("login.html", error=error)
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        if request.form["sub"] == "Submit":
            name = request.form["name"]
            email = request.form["email"]
            password = request.form["password"]
            rpassword = request.form["rpassword"]
            pet = request.form["pet"]
            if password != rpassword:
                error = "Password dose not match..!!!"
                return render_template("register.html", error=error)
            try:
                con = sqlite3.connect("mydatabase.db")
                cursorObj = con.cursor()
                cursorObj.execute(
                    f"SELECT Name from Users WHERE Email='{email}' AND password = '{password}';"
                )

                if cursorObj.fetchone():
                    error = "User already Registered...!!!"
                    return render_template("register.html", error=error)
            except:
                pass
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            con = sqlite3.connect("mydatabase.db")
            cursorObj = con.cursor()
            cursorObj.execute(
                "CREATE TABLE IF NOT EXISTS Users (Date text,Name text,Email text,password text,pet text)"
            )
            cursorObj.execute(
                "INSERT INTO Users VALUES(?,?,?,?,?)",
                (dt_string, name, email, password, pet),
            )
            con.commit()

            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    error = None
    global name
    if request.method == "POST":
        email = request.form["email"]
        pet = request.form["pet"]
        con = sqlite3.connect("mydatabase.db")
        cursorObj = con.cursor()
        cursorObj.execute(
            f"SELECT password from Users WHERE Email='{email}' AND pet = '{pet}';"
        )

        try:
            password = cursorObj.fetchone()
            # print(password)
            error = "Your password : " + password[0]
        except:
            error = "Invalid information Please try again..!!!"
        return render_template("forgot-password.html", error=error)
    return render_template("forgot-password.html")


@app.route("/home", methods=["GET", "POST"])
def home():
    global name
    return render_template("home.html", name=name)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    return render_template("dashboard.html", name=name)

@app.route("/upload_and_image", methods=["GET", "POST"])
def upload_and_image():
    global paragraph
    global name

    error = ""
    success = ""

    if request.method == "POST":
        # Check which form was submitted
        if "submit_link" in request.form:
            # Process YouTube Link
            link = request.form.get("link")
            try:
                # Download and process the audio from the YouTube link
                name = download_audio(link)
                paragraph = transcribe_audio("audio.wav")

                # Check if content is finance-related
                if is_finance_related(paragraph):
                    paragraph = model.restore_punctuation(paragraph)
                    success = "YouTube video processed successfully and is related to Finance."
                    return redirect(url_for("qa"))  # Redirect to the QA page
                else:
                    error = "The provided YouTube video is not related to Finance."
            except Exception as e:
                error = f"An error occurred while processing the YouTube link: {str(e)}"

        elif "upload_video" in request.form:
            # Process Uploaded Video
            video_file = request.files.get("video")
            try:
                # Save the uploaded video
                save_path = "upload/"
                if not os.path.exists(save_path):
                    os.makedirs(save_path)  # Create the directory if it doesn't exist

                file_path = os.path.join(save_path, "test.mp4")
                video_file.save(file_path)

                # Extract audio from the video
                clip = VideoFileClip(file_path)
                clip.audio.write_audiofile("audio.wav")

                # Split and transcribe the audio
                chunk_paths = split_audio("audio.wav")
                paragraphs = []

                for chunk_path in chunk_paths:
                    audio = sr.AudioFile(chunk_path)
                    with audio as source:
                        audio_file = r.record(source)
                    paragraphs.append(r.recognize_google(audio_file))

                # Combine all the transcriptions
                paragraph = " ".join(paragraphs)

                # Check if content is finance-related
                if is_finance_related(paragraph):
                    paragraph = model.restore_punctuation(paragraph)
                    success = "Video uploaded and processed successfully. It is related to Finance."
                    return redirect(url_for("vqa"))  # Redirect to the QA page
                else:
                    error = "The uploaded video is not related to Finance."
            except Exception as e:
                error = f"An error occurred while processing the uploaded video: {str(e)}"

    # Render the combined page with error/success messages
    return render_template(
        "upload_and_image.html",
        link=None,
        error=error,
        success=success,
    )

@app.route("/image", methods=["GET", "POST"])
def image():
    global paragraph
    global name

    if request.method == "POST":
        error = ""
        success = ""
        link = request.form["link"]

        try:
            # Download audio and transcribe
            name = download_audio(link)  # Save audio as audio.wav
            paragraph = transcribe_audio("audio.wav")

            # Check if the content is finance-related
            is_finance = is_finance_related(paragraph)

            if is_finance:
                paragraph = model.restore_punctuation(
                    paragraph
                )  
                return redirect(url_for("qa"))
            else:
                error = "This video is not related to Finance. Please provide another video link."

        except Exception as e:
            # Catch any unexpected errors and provide feedback
            error = f"An error occurred: {str(e)}. Please try again."

        return render_template(
            "image.html",
            name=name,
            link=link,
            paragraph=paragraph,
            error=error,
            success=success,
        )

    return render_template("image.html", name=name)


@app.route("/qa", methods=["GET", "POST"])
def qa():
    global name
    global paragraph

    askBot(
        "This is transcribe text from the video: "
        + paragraph
        + "------------------------"
        " read given video Script properly next i'll ask some questions on it, give me answers related to this videoScript only and give simple and short answers "
    )

    if request.method == "POST":
        que = request.form["que"]
        # print(paragraph)
        answer = askBot(que)
        return render_template("qa.html", name=name, que=que, answer=answer)
    return render_template("qa.html", name=name)




@app.route("/upload", methods=["GET", "POST"])
def upload():
    global paragraph  # Store paragraph globally for reuse in `videoQA`
    error = ""
    success = ""

    if request.method == "POST":
        try:
            # Save the uploaded video file
            savepath = "upload/"
            f = request.files["doc"]
            filepath = os.path.join(savepath, secure_filename("test.mp4"))
            f.save(filepath)

            # Extract audio from the video
            clip = VideoFileClip(filepath)
            clip.audio.write_audiofile("audio.wav")

            # Split and transcribe the audio
            chunk_paths = split_audio("audio.wav")
            paragraphs = []

            for chunk_path in chunk_paths:
                audio = sr.AudioFile(chunk_path)
                with audio as source:
                    audio_file = r.record(source)
                paragraphs.append(r.recognize_google(audio_file))

            # Combine all the transcriptions
            paragraph = " ".join(paragraphs)

            # Check if the content is finance-related
            if is_finance_related(paragraph):
                # Redirect to videoQA page with the transcribed paragraph
                return redirect(url_for("vqa"))
            else:
                error = "This video is not related to Finance. Please upload another video."
        
        except Exception as e:
            error = f"An error occurred during processing: {str(e)}"
            print(error)

    return render_template("upload.html", error=error, success=success)




# @app.route("/videoQA", methods=["GET", "POST"])
# def vqa():
#     global name
#     global paragraph

#     clip = VideoFileClip("upload/test.mp4")
#     clip.audio.write_audiofile("audio.wav")
#     audio = sr.AudioFile("audio.wav")
#     chunk_paths = split_audio("audio.wav")
#     paragraphs = []

#     for chunk_path in chunk_paths:
#                 # Transcribe each chunk
#                 audio = sr.AudioFile(chunk_path)
#                 with audio as source:
#                     audio_file = r.record(source)
#                 paragraphs.append(r.recognize_google(audio_file))

#     # Combine all the transcriptions
#     paragraph = " ".join(paragraphs)


#     askBot(
#         "This is transcribe text from the video: "
#         + paragraph
#         + "------------------------"
#         " read given paragraph properly next i'll ask some questions on it, give me answers related to this paragraph only and give simple and short answers"
#     )

#     if request.method == "POST":
#         que = request.form["que"]
#         # print(paragraph)
#         answer = askBot(que)
#         return render_template(
#             "videoQA.html",
#             name=name,
#             que=que,
#             answer=answer,
#             paragraph=paragraph
            
#         )
#     return render_template("videoQA.html", name=name, paragraph=paragraph)
@app.route("/videoQA", methods=["GET", "POST"])
def vqa():
    global paragraph  
    # print(paragraph)
    askBot(
        "This is transcribe text from the video: "
        + paragraph
        + "------------------------"
        " read given video Script properly next i'll ask some questions on it, give me answers related to this videoScript only and give simple and short answers "
    )
    if request.method == "POST":
        que = request.form["que"]
        answer = askBot(que)
        return render_template(
            "videoQA.html",
            paragraph=paragraph,
            que=que,
            answer=answer,
        )

    return render_template("videoQA.html", paragraph=paragraph)


# No caching at all for API endpoints.
@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    return response


if __name__ == "__main__" and run:
    app.run(host="0.0.0.0", debug=True, threaded=True)
