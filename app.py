import json
from groq import Groq
from pypdf import PdfReader
import os
from flask import Flask, redirect,render_template,request,session, url_for
os.makedirs("uploads", exist_ok=True)
from dotenv import load_dotenv
load_dotenv()
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)
app = Flask(__name__)
app.secret_key = "resume-analyzer"
@app.route("/", methods=["GET", "POST"])
def home_page():
    if request.method == "POST":

        resume = request.files["resume_file"]
        description = request.form["description"]

        resume.save("uploads/" + resume.filename)
        resume_file = "uploads/" + resume.filename

        reader = PdfReader(resume_file)
        pages = reader.pages

        resume_text = ""

        for i in pages:
            page_text = i.extract_text()

            if page_text is None:
                print("Page extract nothing")
            else:
                resume_text += page_text

        if resume_text == "":
            print("YOUR UPLOADED RESUME FILE CONTAINS UNEXTRACTABLE TEXT")

        session["messages"] = [{
            "role": "system",
            "content":
            "Role:\n"
            "You are an ATS Resume Analyzer.\n"
            "Analyze the resume against the job description.\n"
            "Return ONLY raw JSON.\n"
            "Do not use markdown.\n"
            "Do not use ```json.\n"
            "Do not include any text before or after JSON.\n"
            "Required fields:\n"
            "- summary\n"
            "- match_score\n"
            "- matching_skills\n"
            "- missing_skills\n"
            "- strengths\n"
            "- weaknesses\n"
            "- recommendation\n\n"
            "Job Description:\n"
            + description +
            "\n\nResume:\n"
            + resume_text
        }]

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=session.get("messages", [])
        )

        bot_response = response.choices[0].message.content


        clean_json = (
            bot_response
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        try:
            report = json.loads(clean_json)
        except Exception as e:
            ("JSON ERROR:", e)

            report = {
                "summary": bot_response,
                "match_score": "N/A",
                "matching_skills": [],
                "missing_skills": [],
                "strengths": [],
                "weaknesses": [],
                "recommendation": []
            }
        score = report.get("match_score")

        if isinstance(score, (int, float)) and score <= 1:
          report["match_score"] = int(score * 100)
        session["report"] = report
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
        report = session.get("report", {})

        messages = [
            {
                "role": "system",
                "content":
                f"""
                You are an expert Career Counselor and Resume Mentor.

                Resume Analysis:
                Summary: {report.get('summary', '')}
                Strengths: {report.get('strengths', [])}
                Weaknesses: {report.get('weaknesses', [])}
                Missing Skills: {report.get('missing_skills', [])}

                The ATS report has already been shown to the user.

                Do NOT repeat the ATS report.
                Do NOT return JSON.
                Do NOT repeat the summary, strengths, weaknesses, or match score unless specifically asked.

                Instead:
                - Give personalized career advice.
                - Suggest projects to build.
                - Suggest skills to learn.
                - Suggest resume improvements.
                - Suggest interview preparation tips.
                - Suggest learning resources.
                - Answer naturally like a mentor.
                """
            }
        ]

        messages.append({
            "role": "user",
            "content": question
        })
        response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
         )

        bot_response = response.choices[0].message.content
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