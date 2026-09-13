import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from passlib.context import CryptContext
from bson import ObjectId
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from pydantic import BaseModel
import fitz
import json
import urllib.request
import urllib.error


# =========================================================
# APP
# =========================================================

app = FastAPI(title="StudyX API")


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# MONGODB
# =========================================================

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI is missing from .env")

client = MongoClient(MONGO_URI)

db = client["studyx"]

users_collection = db["users"]
materials_collection = db["materials"]
material_chunks_collection = db["material_chunks"]
study_plans_collection = db["study_plans"]


# =========================================================
# PASSWORD HASHING
# =========================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# =========================================================
# EMBEDDING MODEL
# =========================================================

print("Loading embedding model...")

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Embedding model loaded successfully!")


# =========================================================
# OLLAMA SETTINGS
# =========================================================

OLLAMA_URL = (
    "http://127.0.0.1:11434/api/generate"
)

OLLAMA_MODEL = "qwen2.5:3b"


# =========================================================
# MODELS
# =========================================================

class RegisterUser(BaseModel):
    name: str
    email: str
    password: str


class LoginUser(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    message: str
    email: str = ""


class SearchRequest(BaseModel):
    question: str
    email: str
    top_k: int = 3


class QuizRequest(BaseModel):
    email: str
    material_id: str = ""
    number_of_questions: int = 5
    difficulty: str = "medium"


# =========================================================
# TEXT CHUNKING
# =========================================================

def create_chunks(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150
):

    text = " ".join(text.split())

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        if end < len(text):

            last_space = text.rfind(
                " ",
                start,
                end
            )

            if last_space > start:
                end = last_space

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(
            end - overlap,
            start + 1
        )

    return chunks


# =========================================================
# OLLAMA AI FUNCTION
# =========================================================

def ask_ollama(prompt: str, json_mode: bool = False):

    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096
        }
    }

    # Ollama JSON mode forces the model to return valid JSON.
    if json_mode:
        data["format"] = "json"

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=300
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

            return result.get(
                "response",
                ""
            ).strip()

    except urllib.error.URLError:

        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama is not running. "
                "Please start Ollama first."
            )
        )

    except Exception as error:

        print(
            "Ollama Error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="AI model could not generate a response."
        )


# =========================================================
# VECTOR SEARCH FUNCTION
# =========================================================

def find_relevant_chunks(
    question: str,
    email: str,
    top_k: int = 3
):

    question_embedding = (
        embedding_model
        .encode(question)
        .tolist()
    )

    chunks = material_chunks_collection.find({

        "email": email,

        "embedding": {
            "$exists": True
        }

    })

    scored_chunks = []

    for chunk in chunks:

        stored_embedding = chunk.get(
            "embedding"
        )

        if not stored_embedding:
            continue

        similarity = cosine_similarity(
            [question_embedding],
            [stored_embedding]
        )[0][0]

        scored_chunks.append({

            "filename":
                chunk["filename"],

            "chunk_index":
                chunk["chunk_index"],

            "text":
                chunk["text"],

            "similarity":
                float(similarity)

        })

    scored_chunks.sort(
        key=lambda x:
            x["similarity"],
        reverse=True
    )

    return scored_chunks[:top_k]


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {

        "message":
            "StudyX is running 🚀",

        "database":
            "MongoDB connected",

        "embedding":
            "Enabled",

        "ai_model":
            OLLAMA_MODEL

    }


# =========================================================
# REGISTER
# =========================================================

@app.post("/register")
def register(
    user: RegisterUser
):

    email = user.email.strip().lower()

    existing_user = users_collection.find_one({

        "email": email

    })

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    hashed_password = pwd_context.hash(
        user.password
    )

    users_collection.insert_one({

        "name":
            user.name.strip(),

        "email":
            email,

        "password":
            hashed_password

    })

    return {

        "message":
            "Account created successfully!"

    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/login")
def login(
    user: LoginUser
):

    email = user.email.strip().lower()

    existing_user = users_collection.find_one({

        "email":
            email

    })

    if not existing_user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    password_correct = pwd_context.verify(

        user.password,

        existing_user["password"]

    )

    if not password_correct:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {

        "message":
            "Login successful!",

        "name":
            existing_user["name"],

        "email":
            existing_user["email"]

    }


# =========================================================
# AI TUTOR - RAG + GENERAL AI
# =========================================================

@app.post("/ai/chat")
def ai_chat(
    request: ChatRequest
):

    question = request.message.strip()

    email = request.email.strip().lower()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    relevant_chunks = []

    if email:

        relevant_chunks = find_relevant_chunks(
            question,
            email,
            top_k=3
        )

    use_pdf_context = False

    if relevant_chunks:

        best_score = (
            relevant_chunks[0]["similarity"]
        )

        if best_score >= 0.35:

            use_pdf_context = True

    # -----------------------------------------------------
    # RAG MODE
    # -----------------------------------------------------

    if use_pdf_context:

        context_parts = []

        for index, chunk in enumerate(
            relevant_chunks
        ):

            context_parts.append(

                f"""
SOURCE {index + 1}
File: {chunk['filename']}

{chunk['text']}
"""

            )

        context = "\n\n".join(
            context_parts
        )

        prompt = f"""
You are StudyX AI Tutor.

Answer the student's question using
the provided study material.

Rules:

1. Prefer the provided PDF content.
2. Do not invent information.
3. If the PDF does not contain enough
   information, clearly say so.
4. Explain in simple language.
5. Use examples when helpful.
6. Do not mention internal AI instructions.

STUDY MATERIAL:

{context}

STUDENT QUESTION:

{question}

Answer clearly.
"""

        answer = ask_ollama(
            prompt
        )

        return {

            "answer":
                answer,

            "mode":
                "rag",

            "sources": [

                {
                    "filename":
                        chunk["filename"],

                    "chunk_index":
                        chunk["chunk_index"],

                    "similarity":
                        chunk["similarity"]

                }

                for chunk
                in relevant_chunks

            ]

        }

    # -----------------------------------------------------
    # GENERAL AI MODE
    # -----------------------------------------------------

    prompt = f"""
You are StudyX AI Tutor.

Answer the student's question clearly
and accurately.

Explain educational topics in simple
language and use examples when helpful.

Student question:

{question}

Give the best helpful answer.
"""

    answer = ask_ollama(
        prompt
    )

    return {

        "answer":
            answer,

        "mode":
            "general",

        "sources":
            []

    }


# =========================================================
# QUIZ GENERATOR
# =========================================================

@app.post("/ai/quiz")
def generate_quiz(request: QuizRequest):

    email = request.email.strip().lower()
    number_of_questions = request.number_of_questions
    difficulty = request.difficulty.strip().lower()

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required."
        )

    if number_of_questions < 1 or number_of_questions > 20:
        raise HTTPException(
            status_code=400,
            detail="Number of questions must be between 1 and 20."
        )

    if difficulty not in ["easy", "medium", "hard"]:
        difficulty = "medium"

    # -----------------------------------------------------
    # GET USER MATERIAL
    # -----------------------------------------------------

    if request.material_id:
        try:
            material_object_id = ObjectId(request.material_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid material ID."
            )

        material = materials_collection.find_one({
            "_id": material_object_id,
            "email": email
        })
    else:
        material = materials_collection.find_one({
            "email": email
        })

    if not material:
        raise HTTPException(
            status_code=404,
            detail="No study material found."
        )

    # -----------------------------------------------------
    # GET MATERIAL CHUNKS
    # -----------------------------------------------------

    chunks = material_chunks_collection.find({
        "material_id": material["_id"],
        "email": email
    }).sort("chunk_index", 1)

    chunk_texts = [chunk.get("text", "") for chunk in chunks]
    chunk_texts = [text.strip() for text in chunk_texts if text.strip()]

    if not chunk_texts:
        raise HTTPException(
            status_code=404,
            detail="No chunks found for this material."
        )

    # Keep the local model prompt reasonably small.
    context = "\n\n".join(chunk_texts[:6])

    # -----------------------------------------------------
    # QUIZ PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are StudyX Quiz Generator.

Create exactly {number_of_questions} multiple-choice questions using ONLY the study material below.
Difficulty: {difficulty}

STRICT RULES:
1. Return a JSON OBJECT, not markdown and not plain text.
2. The object must contain exactly one key: "questions".
3. "questions" must be an array containing exactly {number_of_questions} objects.
4. Every question object must contain exactly these keys:
   "question", "options", "correct_answer"
5. "options" must contain exactly 4 different strings.
6. "correct_answer" must be exactly one of the 4 option strings.
7. Base every question on the study material.
8. Do not add explanations, notes, prefixes, suffixes, or code fences.

OUTPUT STRUCTURE:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A"
    }}
  ]
}}

STUDY MATERIAL:
{context}
"""

    # -----------------------------------------------------
    # ASK OLLAMA IN JSON MODE
    # -----------------------------------------------------

    raw_response = ask_ollama(prompt, json_mode=True)

    # -----------------------------------------------------
    # ROBUST JSON EXTRACTION
    # -----------------------------------------------------

    cleaned_response = raw_response.strip()
    cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned_response)
    except json.JSONDecodeError:
        # Sometimes a local model adds a small amount of text around JSON.
        # Extract the first complete JSON object from the response.
        first = cleaned_response.find("{")
        last = cleaned_response.rfind("}")

        if first == -1 or last <= first:
            print("Quiz JSON Error:", raw_response)
            raise HTTPException(
                status_code=500,
                detail="AI returned an invalid quiz format."
            )

        try:
            parsed = json.loads(cleaned_response[first:last + 1])
        except json.JSONDecodeError:
            print("Quiz JSON Error:", raw_response)
            raise HTTPException(
                status_code=500,
                detail="AI returned an invalid quiz format."
            )

    # -----------------------------------------------------
    # ACCEPT OBJECT OR ARRAY
    # -----------------------------------------------------

    if isinstance(parsed, dict):
        quiz = parsed.get("questions", [])
    elif isinstance(parsed, list):
        quiz = parsed
    else:
        quiz = []

    # -----------------------------------------------------
    # VALIDATE QUESTIONS
    # -----------------------------------------------------

    valid_questions = []

    for item in quiz:
        if not isinstance(item, dict):
            continue

        question = item.get("question")
        options = item.get("options")
        correct_answer = item.get("correct_answer")

        if not isinstance(question, str) or not question.strip():
            continue

        if not isinstance(options, list) or len(options) != 4:
            continue

        options = [str(option).strip() for option in options]

        if any(not option for option in options):
            continue

        if len(set(options)) != 4:
            continue

        if not isinstance(correct_answer, str):
            continue

        if correct_answer not in options:
            continue

        valid_questions.append({
            "question": question.strip(),
            "options": options,
            "correct_answer": correct_answer.strip()
        })

    # -----------------------------------------------------
    # FINAL CHECK
    # -----------------------------------------------------

    if len(valid_questions) < number_of_questions:
        print("Invalid/insufficient quiz response:", raw_response)
        raise HTTPException(
            status_code=500,
            detail=(
                f"AI generated only {len(valid_questions)} valid questions "
                f"out of {number_of_questions}. Please try again."
            )
        )

    valid_questions = valid_questions[:number_of_questions]

    return {
        "message": "Quiz generated successfully!",
        "filename": material["filename"],
        "difficulty": difficulty,
        "questions": valid_questions
    }


# =========================================================
# PDF UPLOAD + AUTOMATIC EMBEDDINGS
# =========================================================

@app.post("/materials/upload")
async def upload_material(
    request: Request
):

    try:

        form = await request.form()

        file = form.get("file")

        email = (

            request.query_params.get(
                "email"
            )

            or str(
                form.get("email") or ""
            )

        )

        if not email:

            raise HTTPException(
                status_code=400,
                detail="User email is required."
            )

        if file is None:

            raise HTTPException(
                status_code=400,
                detail="PDF file is required."
            )

        if not file.filename.lower().endswith(
            ".pdf"
        ):

            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported."
            )

        file_data = await file.read()

        pdf = fitz.open(

            stream=file_data,

            filetype="pdf"

        )

        extracted_text = ""

        for page in pdf:

            extracted_text += (
                page.get_text()
            )

        page_count = len(pdf)

        pdf.close()


        # Create chunks
        chunks = create_chunks(

            extracted_text,

            chunk_size=1000,

            overlap=150

        )


        # Save material
        material = {

            "filename":
                file.filename,

            "email":
                email.strip().lower(),

            "pages":
                page_count,

            "text":
                extracted_text,

            "text_length":
                len(extracted_text),

            "chunk_count":
                len(chunks)

        }

        result = (
            materials_collection
            .insert_one(material)
        )

        material_id = (
            result.inserted_id
        )


        # Create embeddings
        print(
            f"Generating embeddings for "
            f"{len(chunks)} chunks..."
        )

        chunk_documents = []

        for index, chunk in enumerate(
            chunks
        ):

            embedding = (
                embedding_model
                .encode(chunk)
                .tolist()
            )

            chunk_documents.append({

                "material_id":
                    material_id,

                "email":
                    email.strip().lower(),

                "filename":
                    file.filename,

                "chunk_index":
                    index,

                "text":
                    chunk,

                "text_length":
                    len(chunk),

                "embedding":
                    embedding,

                "embedding_model":
                    "all-MiniLM-L6-v2"

            })


        if chunk_documents:

            material_chunks_collection.insert_many(
                chunk_documents
            )


        print(
            "Embeddings generated successfully!"
        )


        return {

            "message":
                "PDF uploaded, chunked and embedded successfully!",

            "material_id":
                str(material_id),

            "filename":
                file.filename,

            "pages":
                page_count,

            "text_length":
                len(extracted_text),

            "chunk_count":
                len(chunks),

            "embeddings":
                "Generated automatically"

        }


    except HTTPException:

        raise


    except Exception as error:

        print(
            "Upload Error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to process PDF."
        )


# =========================================================
# GET USER MATERIALS
# =========================================================

@app.get("/materials")
def get_materials(
    email: str
):

    email = email.strip().lower()

    materials = materials_collection.find(

        {
            "email":
                email
        },

        {
            "text":
                0
        }

    ).sort(

        "_id",
        -1

    )

    result = []

    for material in materials:

        result.append({

            "id":
                str(material["_id"]),

            "filename":
                material["filename"],

            "pages":
                material["pages"],

            "text_length":
                material["text_length"],

            "chunk_count":
                material.get(
                    "chunk_count",
                    0
                )

        })

    return {

        "materials":
            result

    }


# =========================================================
# GET MATERIAL CHUNKS
# =========================================================

@app.get(
    "/materials/{material_id}/chunks"
)
def get_material_chunks(
    material_id: str
):

    try:

        object_id = ObjectId(
            material_id
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid material ID."
        )

    chunks = (
        material_chunks_collection
        .find({
            "material_id":
                object_id
        })
        .sort(
            "chunk_index",
            1
        )
    )

    result = []

    for chunk in chunks:

        result.append({

            "id":
                str(chunk["_id"]),

            "chunk_index":
                chunk["chunk_index"],

            "text":
                chunk["text"]

        })

    return {

        "material_id":
            material_id,

        "chunks":
            result

    }


# =========================================================
# VECTOR SEARCH
# =========================================================

@app.post("/ai/search")
def vector_search(
    request: SearchRequest
):

    question = request.question.strip()

    email = request.email.strip().lower()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    results = find_relevant_chunks(

        question,

        email,

        request.top_k

    )

    return {

        "question":
            question,

        "results":
            results

    }


# =========================================================
# DELETE MATERIAL
# =========================================================

@app.delete(
    "/materials/{material_id}"
)
def delete_material(
    material_id: str
):

    try:

        object_id = ObjectId(
            material_id
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid material ID."
        )

    result = (
        materials_collection
        .delete_one({
            "_id":
                object_id
        })
    )

    if result.deleted_count == 0:

        raise HTTPException(
            status_code=404,
            detail="Material not found."
        )


    # Delete related chunks
    material_chunks_collection.delete_many({

        "material_id":
            object_id

    })


    return {

        "message":
            "Material and its chunks deleted successfully!"

    }
# =========================================================
# AI STUDY PLANNER
# =========================================================

class StudyPlanRequest(BaseModel):
    email: str
    goal: str
    subject: str
    exam_date: str
    daily_hours: int = 2
    level: str = "intermediate"
    topics: str


@app.post("/ai/study-plan")
def generate_study_plan(
    request: StudyPlanRequest
):

    email = request.email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required."
        )

    if not request.goal.strip():
        raise HTTPException(
            status_code=400,
            detail="Study goal is required."
        )

    if not request.subject.strip():
        raise HTTPException(
            status_code=400,
            detail="Subject is required."
        )

    if not request.exam_date.strip():
        raise HTTPException(
            status_code=400,
            detail="Exam date is required."
        )

    if not request.topics.strip():
        raise HTTPException(
            status_code=400,
            detail="Topics are required."
        )

    if request.daily_hours < 1 or request.daily_hours > 10:
        raise HTTPException(
            status_code=400,
            detail="Daily study hours must be between 1 and 10."
        )


    # -----------------------------------------------------
    # AI PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are StudyX, an AI study planning assistant.

Create a realistic and practical study plan for a student.

Student Goal:
{request.goal}

Subject:
{request.subject}

Exam / Target Date:
{request.exam_date}

Daily Study Time:
{request.daily_hours} hours

Current Level:
{request.level}

Topics / Syllabus:
{request.topics}

IMPORTANT:
Return ONLY valid JSON.
Do not use markdown.
Do not add any explanation outside JSON.

Use exactly this structure:

{{
    "title": "Personalized Study Plan",
    "summary": "Short summary of the study plan",
    "days": [
        {{
            "date": "Day 1",
            "tasks": [
                {{
                    "topic": "Topic name",
                    "activity": "What the student should study or practice",
                    "hours": 1
                }}
            ]
        }}
    ]
}}

Rules:

1. Divide the syllabus across realistic study days.
2. Do not overload a single day.
3. Respect the daily study time.
4. Include learning, practice and revision.
5. Start with easier topics.
6. Gradually move toward harder topics.
7. Include final revision before the exam date.
8. Keep activities specific and useful.
9. "hours" must always be a number.
10. Return only valid JSON.
"""


    # -----------------------------------------------------
    # ASK OLLAMA
    # -----------------------------------------------------

    raw_response = ask_ollama(prompt)

    cleaned_response = raw_response.strip()


    # -----------------------------------------------------
    # REMOVE MARKDOWN
    # -----------------------------------------------------

    if cleaned_response.startswith("```json"):

        cleaned_response = (
            cleaned_response
            .replace("```json", "", 1)
            .replace("```", "")
            .strip()
        )

    elif cleaned_response.startswith("```"):

        cleaned_response = (
            cleaned_response
            .replace("```", "")
            .strip()
        )


    # -----------------------------------------------------
    # PARSE JSON
    # -----------------------------------------------------

    try:

        plan = json.loads(
            cleaned_response
        )

    except json.JSONDecodeError:

        print(
            "Study Plan JSON Error:",
            raw_response
        )

        raise HTTPException(
            status_code=500,
            detail="AI returned an invalid study plan format."
        )


    # -----------------------------------------------------
    # VALIDATE PLAN
    # -----------------------------------------------------

    if not isinstance(plan, dict):

        raise HTTPException(
            status_code=500,
            detail="Invalid study plan format."
        )


    if "days" not in plan:

        raise HTTPException(
            status_code=500,
            detail="Study plan does not contain days."
        )


    if not isinstance(plan["days"], list):

        raise HTTPException(
            status_code=500,
            detail="Invalid study plan days format."
        )


    # -----------------------------------------------------
    # SAVE STUDY PLAN TO MONGODB
    # -----------------------------------------------------

    study_plan_document = {
        "email": email,
        "goal": request.goal.strip(),
        "subject": request.subject.strip(),
        "exam_date": request.exam_date.strip(),
        "daily_hours": request.daily_hours,
        "level": request.level.strip().lower(),
        "topics": request.topics.strip(),
        "plan": plan,
        "completed_tasks": [],
        "created_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )
    }

    result = study_plans_collection.insert_one(
        study_plan_document
    )

    # -----------------------------------------------------
    # RETURN PLAN
    # -----------------------------------------------------

    return {
        "message": "Study plan generated and saved successfully!",
        "email": email,
        "plan_id": str(result.inserted_id),
        "plan": plan,
        "completed_tasks": []
    }
# =========================================================
# GET SAVED STUDY PLANS
# =========================================================

@app.get("/study-plans")
def get_study_plans(email: str):

    email = email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required."
        )

    plans = study_plans_collection.find(
        {"email": email}
    ).sort(
        "created_at",
        -1
    )

    result = []

    for plan in plans:
        result.append({
            "id": str(plan["_id"]),
            "goal": plan.get("goal", ""),
            "subject": plan.get("subject", ""),
            "exam_date": plan.get("exam_date", ""),
            "daily_hours": plan.get("daily_hours", 0),
            "level": plan.get("level", "intermediate"),
            "topics": plan.get("topics", ""),
            "plan": plan.get("plan", {}),
            "completed_tasks": plan.get("completed_tasks", []),
            "created_at": plan.get("created_at")
        })

    return {
        "email": email,
        "plans": result
    }


# =========================================================
# STUDY PLAN TASK COMPLETION
# =========================================================

class StudyTaskCompletionRequest(BaseModel):
    email: str
    day_index: int
    task_index: int
    completed: bool


@app.post("/study-plans/{plan_id}/task")
def update_study_task(
    plan_id: str,
    request: StudyTaskCompletionRequest
):

    email = request.email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required."
        )

    if request.day_index < 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid day index."
        )

    if request.task_index < 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid task index."
        )

    try:
        plan_object_id = ObjectId(plan_id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid study plan ID."
        )

    study_plan = study_plans_collection.find_one({
        "_id": plan_object_id,
        "email": email
    })

    if not study_plan:
        raise HTTPException(
            status_code=404,
            detail="Study plan not found."
        )

    plan = study_plan.get("plan", {})
    days = plan.get("days", [])

    if (
        request.day_index >= len(days)
        or not isinstance(days[request.day_index], dict)
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid study day."
        )

    tasks = days[request.day_index].get("tasks", [])

    if request.task_index >= len(tasks):
        raise HTTPException(
            status_code=400,
            detail="Invalid study task."
        )

    task_key = f"{request.day_index}-{request.task_index}"

    completed_tasks = study_plan.get(
        "completed_tasks",
        []
    )

    if not isinstance(completed_tasks, list):
        completed_tasks = []

    if request.completed:
        if task_key not in completed_tasks:
            completed_tasks.append(task_key)
    else:
        completed_tasks = [
            key
            for key in completed_tasks
            if key != task_key
        ]

    study_plans_collection.update_one(
        {
            "_id": plan_object_id,
            "email": email
        },
        {
            "$set": {
                "completed_tasks": completed_tasks
            }
        }
    )

    return {
        "message": "Task completion updated successfully!",
        "plan_id": plan_id,
        "task": task_key,
        "completed": request.completed,
        "completed_tasks": completed_tasks
    }


# =========================================================
# PROGRESS TRACKING
# =========================================================

progress_collection = db["progress"]


class QuizProgressRequest(BaseModel):
    email: str
    filename: str = "Unknown"
    total_questions: int
    correct_answers: int
    score: float
    percentage: float
    difficulty: str = "medium"


# ---------------------------------------------------------
# SAVE QUIZ RESULT
# ---------------------------------------------------------

@app.post("/progress/quiz")
def save_quiz_progress(
    request: QuizProgressRequest
):

    email = request.email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required."
        )

    if request.total_questions < 1:
        raise HTTPException(
            status_code=400,
            detail="Total questions must be at least 1."
        )

    if request.correct_answers < 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid correct answers."
        )

    if request.correct_answers > request.total_questions:
        raise HTTPException(
            status_code=400,
            detail="Correct answers cannot exceed total questions."
        )


    progress = {
        "email": email,
        "type": "quiz",
        "filename": request.filename,
        "total_questions": request.total_questions,
        "correct_answers": request.correct_answers,
        "score": request.score,
        "percentage": request.percentage,
        "difficulty": request.difficulty,
        "created_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )
    }


    result = progress_collection.insert_one(
        progress
    )


    return {
        "message": "Quiz progress saved successfully!",
        "progress_id": str(result.inserted_id)
    }


# ---------------------------------------------------------
# GET USER PROGRESS
# ---------------------------------------------------------

@app.get("/progress")
def get_progress(email: str):

    email = email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required."
        )


    records = progress_collection.find(
        {
            "email": email
        }
    ).sort(
        "created_at",
        -1
    )


    result = []

    for record in records:

        result.append({
            "id": str(record["_id"]),
            "type": record.get("type", "quiz"),
            "filename": record.get(
                "filename",
                "Unknown"
            ),
            "total_questions": record.get(
                "total_questions",
                0
            ),
            "correct_answers": record.get(
                "correct_answers",
                0
            ),
            "score": record.get(
                "score",
                0
            ),
            "percentage": record.get(
                "percentage",
                0
            ),
            "difficulty": record.get(
                "difficulty",
                "medium"
            ),
            "created_at": record.get(
                "created_at"
            )
        })


    return {
        "email": email,
        "progress": result
    }