from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from PyPDF2 import PdfReader
from docx import Document
from dotenv import load_dotenv
from google import genai
import os
import uvicorn

# Load environment variables
load_dotenv()

app = FastAPI()

# Set up static and template folders
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory session store
user_sessions = {}

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Home routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

# Helper function to read file content
async def read_file_content(file: UploadFile):
    if file.filename.endswith(".pdf"):
        reader = PdfReader(file.file)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    elif file.filename.endswith(".docx"):
        doc = Document(file.file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif file.filename.endswith(".txt"):
        return (await file.read()).decode("utf-8")
    else:
        raise ValueError("Unsupported file type")

# Main endpoint
@app.post("/chat")
async def chat_post(
    request: Request,
    message: str | None = Form(None),
    file: UploadFile | None = None
):
    session_id = request.client.host
    print(f"[CHAT] called; session_id={session_id} file_present={file is not None} message_len={len(message or '')}")
    session_data = user_sessions.get(session_id, {"content": "", "summary": "", "history": []})
    ai_response = ""
    summary = None

    # 🔹 Handle file upload and summarize
    if file:
        try:
            file.file.seek(0)
            content = await read_file_content(file)
            session_data["content"] = content  # Replace old content

            # Summarize immediately
            summary_prompt = f"Summarize this document in a clear and concise way:\n\n{content[:15000]}"
            summary_response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=summary_prompt
            )
            summary = summary_response.text or "Summary not available."

            # Store summary in session
            session_data["summary"] = summary
            session_data["history"] = []  # Reset history after new file
            user_sessions[session_id] = session_data

            return JSONResponse({"summary": summary, "ai": "File uploaded and summarized successfully!"})

        except Exception as e:
            return JSONResponse({"error": f"Error reading file: {str(e)}"}, status_code=400)

    # 🔹 Handle chat question
    elif message:
        if not session_data["summary"]:
            return JSONResponse({"error": "Please upload a file first."}, status_code=400)

        # Use both content and summary for context
        prompt = f"""
You are chatting with a user who uploaded a document. Use the summary below to answer briefly and conversationally. 
Do NOT repeat or restate the summary — just answer the question naturally.

Summary: {session_data['summary']}

Question: {message}
"""


        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            ai_response = response.text or "No response generated."
        except Exception as e:
            ai_response = f"Error: {str(e)}"

        session_data["history"].append({"user": message, "ai": ai_response})
        user_sessions[session_id] = session_data

        return JSONResponse({"user": message, "ai": ai_response})

    else:
        return JSONResponse({"error": "No input provided."}, status_code=400)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
