import json
from ollama import chat
from pypdf import PdfReader
import os
from flask import Flask, redirect,render_template,request,session, url_for
os.makedirs("uploads", exist_ok=True)
app = Flask(__name__)
app.secret_key = "resume-analyzer"
@app.route("/",methods=["GET","POST"])
def home_page():
    if request.method=="POST":
        resume=request.files["resume_file"]
        description=request.form["description"]
        resume.save("uploads/"+ resume.filename)
        resume_file="uploads/"+resume.filename
        reader=PdfReader(resume_file)
        pages=reader.pages
        resume_text=str()
        for i in pages:
            page_text=i.extract_text()
            if page_text is None:
                print("Page",i,"extract nothing")
            else:
                resume_text+=page_text
        if  resume_text=="":
            print("YOUR UPLOADED RESUME FILE CONTAINS UNEXTRACTABLE TEXT \nPLEASE ENTER VALID FILE")
        session["messages"]=[{
        "role": "system",
        "content":
        " Role:\n"
        "You are an ATS Resume Analyzer.\n" 
        "Your task:\n"
        "Analyze the resume against the job description\n"
        "Provide concise and actionable answers.\n"
        "Do not add explanations before or after JSON.Return only valid JSON.\n"
        "Required fields:\n"
        "- summary\n"
        "- match_score\n"
        "- matching_skills\n"
        "- missing_skills\n"
        "- strengths\n"
        "- weaknesses\n"
        "- recommendation\n"
        "Job Description:\n"
            + description +
        "\n\nResume:\n"
            + resume_text 
        }]
        response=chat(
        model="qwen2.5:3b",
        messages=session.get("messages",[])
        )
        bot_response=response.message.content
        report = json.loads(bot_response)
        session["report"]=report
        return redirect(url_for("report_page"))
    return render_template("index.html")
@app.route("/report")
def report_page():
    report = session.get("report")
    return render_template("report.html", report=report)

@app.route("/chats",methods=["GET","POST"])
def chat_page():
    bot_response = ""
    if request.method=="POST":
        question=request.form["question"]
        messages=session.get("messages",[])
        messages.append({
            "role": "system",
            "content":
            "You are an AI Career Counselor and Resume Advisor.\n"
            "Use the provided resume and job description as context.\n"
            "Answer the user's questions about their resume, skills, career growth, interview readiness, and job fit.\n"
            "Provide concise, practical, and actionable advice.\n"
            "Do not return JSON unless explicitly requested.\n"
            })
        messages.append({
                "role":"user",
                "content":question
        })
        response=chat(
        model="qwen2.5:3b",
        messages=messages
        )
        bot_response=response.message.content
        messages.append({
        "role":"assistant",
        "content":bot_response
        })
        session["messages"] = messages
    return render_template(
        "chat_page.html",
         bot_response=bot_response
        )
if __name__=="__main__":
    app.run(debug=True)