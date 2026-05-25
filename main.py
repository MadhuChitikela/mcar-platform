import os
import time
import json
import io
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcar_backend")

# Try to initialize Gemini API
GEMINI_AVAILABLE = False
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here" and len(GEMINI_API_KEY.strip()) > 10:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
        logger.info("Google Gemini API successfully initialized!")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini API: {e}")
else:
    logger.warning("Gemini API key is missing or default placeholder. Using advanced local simulator.")

# Try importing pypdf for PDF processing
PDF_PARSING_AVAILABLE = False
try:
    from pypdf import PdfReader
    PDF_PARSING_AVAILABLE = True
    logger.info("pypdf successfully loaded for PDF Knowledge Base uploads!")
except ImportError:
    logger.warning("pypdf not found. PDF text extraction will fallback to binary decode.")

app = FastAPI(title="MCAR AI Business Automation Platform")

# In-Memory Database for Conversations, RAG Chunks, and Appointments
conversations_db: Dict[str, Dict[str, Any]] = {}
rag_knowledge_base: str = ""
rag_chunks: List[str] = []
rag_embeddings: List[List[float]] = []
appointments_db: List[Dict[str, Any]] = []
google_sheets_connected: bool = False

# Business Owner Account configurations (dynamically synced from UI)
owner_settings = {
    "business_name": "Karan & Associates CA",
    "whatsapp": "+91 98765 43210",
    "instagram": "@your_ca_firm",
    "email": "contact@cafirm.com",
    "voice": "+91 12345 67890"
}

# Helper: Create high-fidelity timestamp
def get_timestamp():
    return time.strftime("%H:%M")

# Prepopulate database with gorgeous mock data
def prepopulate_mock_data():
    global conversations_db, appointments_db
    
    conversations_db = {
        "conv_whatsapp_1": {
            "id": "conv_whatsapp_1",
            "name": "Sneha Sharma",
            "channel": "WhatsApp",
            "contact": "+91 98765 43210",
            "unread_count": 0,
            "status": "AI Replied",
            "messages": [
                {"sender": "user", "text": "Hi, I saw your advertisement about AutoSphere business automation tools. Can you share the pricing sheet for the Enterprise tier?", "timestamp": "09:12"},
                {"sender": "ai", "text": "Hello Sneha! Thanks for reaching out to AutoSphere. 🌟 Our Enterprise Plan is tailored for large-scale automation and starts at ₹39,999/month ($499). It includes unlimited AI agents, custom API integrations, dedicated support, and RAG knowledge base setup. \n\nWould you like me to book a quick 10-minute demo call with our engineering lead to discuss your specific scaling requirements?", "timestamp": "09:13"}
            ],
            "lead_profile": {
                "lead_name": "Sneha Sharma",
                "lead_email": "sneha.sharma@tatanex.in",
                "lead_phone": "+91 98765 43210",
                "lead_company": "Tata Nex",
                "lead_interest": "Enterprise Tier Platform",
                "lead_sentiment": "Positive",
                "lead_score": 92,
                "ai_summary": "Highly motivated Indian enterprise lead inquiring about custom API capabilities and high-volume pricing."
            }
        },
        "conv_instagram_1": {
            "id": "conv_instagram_1",
            "name": "Aarav Mehta",
            "channel": "Instagram",
            "contact": "@aarav_mehta_digital",
            "unread_count": 1,
            "status": "Human Takeover",
            "messages": [
                {"sender": "user", "text": "Hey guys! Quick question: does your WhatsApp auto-responder support media attachments like PDFs?", "timestamp": "09:30"},
                {"sender": "ai", "text": "Hi Aarav! 👋 Yes, indeed! Our platform can automatically send and receive PDFs, images, and sheets. It uses AI to parse the uploaded file or send a relevant brochure instantly to the lead.", "timestamp": "09:31"},
                {"sender": "user", "text": "Awesome. I'm actually a developer building this for a client. Do you have a reseller or partner program?", "timestamp": "09:35"}
            ],
            "lead_profile": {
                "lead_name": "Aarav Mehta",
                "lead_email": "aarav@pixelmedia.in",
                "lead_phone": "N/A",
                "lead_company": "Pixel Media Agency",
                "lead_interest": "Reseller / Partnership Program",
                "lead_sentiment": "Positive",
                "lead_score": 85,
                "ai_summary": "Creative agency director from Mumbai inquiring about partnership and reseller programs for multi-client setup."
            }
        },
        "conv_email_1": {
            "id": "conv_email_1",
            "name": "Vikram Malhotra",
            "channel": "Email",
            "contact": "vikram.malhotra@relianceglobal.com",
            "unread_count": 0,
            "status": "Pending",
            "messages": [
                {"sender": "user", "text": "Subject: Partnership Inquiry & CRM Integration\n\nHello Team AutoSphere,\n\nI am Vikram Malhotra, CTO of Reliance Global. We currently handle about 10,000 support calls and SMS per month. We are looking to adopt your system if it integrates with Salesforce CRM. Please send over your technical specifications document.", "timestamp": "08:05"}
            ],
            "lead_profile": {
                "lead_name": "Vikram Malhotra",
                "lead_email": "vikram.malhotra@relianceglobal.com",
                "lead_phone": "N/A",
                "lead_company": "Reliance Global",
                "lead_interest": "Salesforce CRM Integration",
                "lead_sentiment": "Neutral",
                "lead_score": 95,
                "ai_summary": "C-level enterprise buyer interested in high-volume SMS and Salesforce CRM syncing. Very high value lead."
            }
        },
        "conv_phone_1": {
            "id": "conv_phone_1",
            "name": "Ananya Iyer",
            "channel": "Voice Call",
            "contact": "+91 81234 56789",
            "unread_count": 0,
            "status": "AI Replied",
            "messages": [
                {"sender": "user", "text": "[Call Transcribed]: Hello? I wanted to see if your AI voice booking system is active. I would like to book an appointment for tomorrow afternoon around 3 PM for automated demo onboarding.", "timestamp": "10:02"},
                {"sender": "ai", "text": "[Voice Agent]: Hello Ananya! Yes, our automated scheduling is active. I have confirmed your onboarding slot for tomorrow at 3:00 PM IST. An SMS and Email calendar invite with connection details have been dispatched to you. I look forward to your session!", "timestamp": "10:03"}
            ],
            "lead_profile": {
                "lead_name": "Ananya Iyer",
                "lead_email": "ananya.i@iyermedia.in",
                "lead_phone": "+91 81234 56789",
                "lead_company": "Iyer Media",
                "lead_interest": "Voice Booking Integration",
                "lead_sentiment": "Positive",
                "lead_score": 88,
                "ai_summary": "Lead booked a demo onboarding session via the Voice simulator for tomorrow at 3 PM IST."
            }
        }
    }
    
    appointments_db = [
        {"id": "apt_1", "name": "Ananya Iyer", "datetime": "Tomorrow at 3:00 PM IST", "channel": "Voice Call"},
        {"id": "apt_2", "name": "Sneha Sharma", "datetime": "Wednesday at 10:00 AM IST", "channel": "WhatsApp"}
    ]


prepopulate_mock_data()

# Data models
class SimulateMessageRequest(BaseModel):
    channel: str
    message: str
    sender_name: str
    sender_contact: str

class ReplyRequest(BaseModel):
    conv_id: str
    text: str

class RagUploadRequest(BaseModel):
    content: str

class OwnerSettingsRequest(BaseModel):
    business_name: str
    whatsapp: str
    instagram: str
    email: str
    voice: str

# ----------------- RAG VECTOR PROCESSING -----------------

def update_rag_store(text: str):
    """Chunks the RAG text and calculates embeddings using Gemini when available."""
    global rag_chunks, rag_embeddings, rag_knowledge_base
    rag_knowledge_base = text
    
    # Chunking: split text into small logical contexts (~100 words with 20 overlap)
    chunks = []
    words = text.split()
    chunk_size = 100
    overlap = 20
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
            
    rag_chunks = chunks
    rag_embeddings = []
    
    if GEMINI_AVAILABLE and len(rag_chunks) > 0:
        try:
            logger.info(f"Generating Gemini embeddings for {len(rag_chunks)} chunks...")
            for chunk in rag_chunks:
                res = genai.embed_content(
                    model="models/embedding-01",
                    content=chunk,
                    task_type="retrieval_document"
                )
                rag_embeddings.append(res['embedding'])
            logger.info("Successfully generated and cached RAG embeddings!")
        except Exception as e:
            logger.error(f"Failed to generate Gemini embeddings: {e}. Falling back to semantic overlap search.")
            rag_embeddings = []

def get_relevant_rag_context(query: str, top_k: int = 2) -> str:
    """Uses cosine similarity on Gemini embeddings (or fallback) to retrieve relevant text."""
    global rag_chunks, rag_embeddings
    if not rag_chunks:
        return ""
        
    if GEMINI_AVAILABLE and len(rag_embeddings) == len(rag_chunks):
        try:
            # Embed query
            res = genai.embed_content(
                model="models/embedding-01",
                content=query,
                task_type="retrieval_query"
            )
            query_vector = res['embedding']
            
            # Simple Math Cosine Similarity
            import math
            def dot_product(v1, v2):
                return sum(x * y for x, y in zip(v1, v2))
            def magnitude(v):
                return math.sqrt(sum(x * x for x in v))
            
            similarities = []
            q_mag = magnitude(query_vector)
            if q_mag > 0:
                for idx, doc_vector in enumerate(rag_embeddings):
                    d_mag = magnitude(doc_vector)
                    if d_mag > 0:
                        similarity = dot_product(query_vector, doc_vector) / (q_mag * d_mag)
                        similarities.append((similarity, idx))
            
            similarities.sort(reverse=True)
            best_chunks = [rag_chunks[idx] for _, idx in similarities[:top_k]]
            logger.info(f"🔍 RAG Search matched {len(best_chunks)} premium chunks from Gemini Vector Store!")
            return "\n---\n".join(best_chunks)
        except Exception as e:
            logger.error(f"Error querying RAG embeddings: {e}. Running keyword search.")
            
    # Simple overlap keyword fallback
    query_words = set(query.lower().split())
    scored_chunks = []
    for chunk in rag_chunks:
        score = sum(1 for w in query_words if w in chunk.lower())
        scored_chunks.append((score, chunk))
    scored_chunks.sort(reverse=True)
    best_chunks = [chunk for score, chunk in scored_chunks[:top_k] if score > 0]
    return "\n---\n".join(best_chunks) if best_chunks else ""

# ----------------- GEMINI / SIMULATED PIPELINE -----------------

def get_gemini_reply(channel: str, message: str, chat_history: List[Dict[str, str]]) -> str:
    """Uses Gemini API to generate a contextual, channel-specific response, utilizing RAG context if present."""
    global rag_knowledge_base
    
    # RAG lookup
    rag_context = get_relevant_rag_context(message)
    if not rag_context:
        rag_context = rag_knowledge_base if rag_knowledge_base else "AutoSphere Tier Pricing: Starter ($49/mo, 1 AI Agent), Pro ($149/mo, 5 Agents, CRM Sync), Enterprise ($499/mo, Unlimited, Custom RAG Knowledge Base). Built-in Google Sheets connector, multi-channel support for WhatsApp, Instagram, Facebook, and Phone Calls."
    
    # Format chat history for prompt context
    history_str = ""
    for msg in chat_history[-5:]:
        sender_label = "Lead" if msg["sender"] == "user" else "AI Auto-Reply"
        history_str += f"{sender_label}: {msg['text']}\n"
    
    system_instruction = f"""
    You are an intelligent, high-converting Conversational AI representative for "{owner_settings['business_name']}".
    "{owner_settings['business_name']}" is a premium business and CA (Chartered Accountancy) firm offering top-tier accounting, tax audits, GST filings, company formations, and financial planning.
    
    Your role is to respond to incoming enquiries on {channel} arriving on our business handle ({owner_settings['whatsapp'] if channel == 'WhatsApp' else owner_settings['instagram'] if channel == 'Instagram' else owner_settings['email'] if channel == 'Email' else owner_settings['voice']}). 
    Be concise, helpful, friendly, and match the style of the channel. E.g., WhatsApp should be warm with emojis, Email should be professional with a subject or greeting, SMS should be extremely punchy, voice call transcripts should be short and spoken-word friendly.
    
    Your goals:
    1. Answer the customer's query immediately and concisely.
    2. Try to gather missing contact details (Email, Phone, Name, Company) subtly if they aren't provided.
    3. Encourage booking a slot for a professional compliance and accounting consultation.
    
    Additional Context (RAG Knowledge Base):
    ---
    {rag_context}
    ---
    
    Current incoming message: "{message}"
    Recent History:
    {history_str}
    
    Draft only the auto-reply text. Do not include quotes, wrappers, or any system notes.
    """
    
    if GEMINI_AVAILABLE:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(system_instruction)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini generation error: {e}. Falling back to smart simulator.")
            
    # Advanced Smart Simulator Fallback
    message_lower = message.lower()
    biz_name = owner_settings['business_name']
    
    # Pricing queries
    if "pricing" in message_lower or "cost" in message_lower or "price" in message_lower or "fee" in message_lower or "audit" in message_lower:
        if channel == "Email":
            return f"Hello! Thank you for writing to {biz_name}. 🌟\n\nOur professional services are structured as follows:\n- Tax Audit & Compliance filings: Starts from ₹15,000/annum\n- GST Monthly filing packages: Starts from ₹2,500/month\n- Complete Bookkeeping & Corporate Filing: Starts from ₹10,000/month\n\nWe also offer comprehensive business automation and CRM integrations for CA operations. Let us know if you'd like to book a consultation slot this week!\n\nBest regards,\n{biz_name} Consultation Desk"
        elif channel == "Voice Call":
            return f"[Voice Agent]: Understood. At {biz_name}, our basic compliance packages start at fifteen thousand rupees per annum. I can trigger an automated text message with our full professional brochure and calendar link directly to your cell phone. Would you like me to do that?"
        else:
            return f"Hey! 🌟 Our professional services at {biz_name} are extremely competitive. GST filing packages start at just ₹2,500/mo, and complete corporate tax audits start around ₹15,000/annum. Shall I schedule a quick screen-share consultation demo with our senior CA?"
            
    # Appointment/Booking queries
    elif "book" in message_lower or "appointment" in message_lower or "schedule" in message_lower or "demo" in message_lower or "call" in message_lower:
        time_slot = "tomorrow at 2:00 PM" if "tomorrow" in message_lower else "this Friday at 11:00 AM"
        if channel == "Voice Call":
            return f"[Voice Agent]: Excellent choice. I have reserved a priority consultation demo slot with our senior CA for {time_slot} for you. A calendar confirmation has been sent to your registered contact. Talk soon!"
        else:
            return f"I'd be absolutely thrilled to set that up! 📅 I have provisionally reserved a 15-minute live consultation with our principal CA on {time_slot}. Does that slot work for your schedule? If yes, send over your email and I will lock it in!"
  
    # Integration queries
    elif "integrate" in message_lower or "salesforce" in message_lower or "crm" in message_lower or "sheets" in message_lower:
        return "Absolutely, CRM integration is one of our strongest suites! 🔌 We support out-of-the-box sync with Google Sheets, Salesforce, HubSpot, and Zapier. This means any lead gathered by our AI auto-replies gets captured instantly in your sales pipeline. Would you like me to email you our API documentation?"

    # Generic Greetings / Queries
    else:
        if channel == "Voice Call":
            return f"[Voice Agent]: Hello! Thank you for calling {biz_name}. I am your voice booking and query assistant. How can I help optimize your compliance and accounting pipelines today?"
        else:
            return f"Hey there! Thanks for reaching out to {biz_name}. 🚀 We build state-of-the-art conversational AI assistants that handle WhatsApp, Instagram, and web enquiries instantly to capture every lead. How can I help you scale your business operations today?"


def extract_lead_profile(sender_name: str, sender_contact: str, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Uses Gemini API to extract a structured lead profile in JSON format, with a highly-intelligent regex fallback."""
    history_text = "\n".join([f"{msg['sender']}: {msg['text']}" for msg in conversation_history])
    
    prompt = f"""
    Analyze the conversation history below and extract the structured lead profile information.
    Provide the response STRICTLY as a single JSON object with these exact keys:
    "lead_name", "lead_email", "lead_phone", "lead_company", "lead_interest", "lead_sentiment", "lead_score", "ai_summary"
    
    Constraints:
    - lead_score should be an integer between 0 and 100 based on interest level.
    - lead_sentiment should be "Positive", "Neutral", or "Negative".
    - If a field is not mentioned, use "N/A" (or keep what we have).
    
    Sender Metadata:
    Name: {sender_name}
    Contact: {sender_contact}
    
    Conversation History:
    {history_text}
    
    Only output the JSON object. Do not include markdown wraps or backticks.
    """
    
    if GEMINI_AVAILABLE:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            clean_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"Gemini profile extraction failed: {e}. Using intelligent semantic fallback.")

    # Intelligent Fallback Parser
    text_corpus = history_text.lower()
    
    # Infer interest area
    interest = "General Business Automation"
    if "pricing" in text_corpus or "price" in text_corpus:
        interest = "Pricing Sheet / Package Inquiry"
    elif "book" in text_corpus or "demo" in text_corpus:
        interest = "Demo Request & Onboarding"
    elif "integrate" in text_corpus or "crm" in text_corpus:
        interest = "CRM Integration & APIs"
    
    # Sentiment calculation
    sentiment = "Neutral"
    score = 65
    positive_words = ["awesome", "great", "thrilled", "cool", "interested", "upgrade", "pricing", "love", "yes"]
    negative_words = ["bad", "slow", "delayed", "expensive", "no", "cancel", "disappointed"]
    
    pos_count = sum(1 for w in positive_words if w in text_corpus)
    neg_count = sum(1 for w in negative_words if w in text_corpus)
    
    if pos_count > neg_count:
        sentiment = "Positive"
        score = min(75 + (pos_count * 5), 98)
    elif neg_count > pos_count:
        sentiment = "Negative"
        score = max(50 - (neg_count * 10), 15)
        
    # Attempt email/phone parsing
    email = "N/A"
    phone = "N/A"
    company = "N/A"
    
    import re
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', sender_contact + " " + history_text)
    if emails:
        email = emails[0]
        
    phones = re.findall(r'\+?\d[\d\-\s\(\)]{8,}\d', sender_contact + " " + history_text)
    if phones:
        phone = phones[0]
        
    if "@" in sender_contact and not emails:
        email = sender_contact
        
    # Guess company
    if email != "N/A" and "gmail" not in email and "yahoo" not in email and "outlook" not in email:
        domain = email.split("@")[-1].split(".")[0]
        company = domain.capitalize()
    elif "ceo of" in text_corpus:
        parts = text_corpus.split("ceo of")
        if len(parts) > 1:
            company = parts[1].split(".")[0].strip().title()

    # Generate rich summary
    summary = f"Lead {sender_name} contacted via {interest.lower()}. Highly communicative."
    if sentiment == "Positive":
        summary = f"Warm lead requesting details about {interest.lower()}. High intent score of {score}%."
    
    return {
        "lead_name": sender_name,
        "lead_email": email,
        "lead_phone": phone,
        "lead_company": company,
        "lead_interest": interest,
        "lead_sentiment": sentiment,
        "lead_score": score,
        "ai_summary": summary
    }

# ----------------- FASTAPI ROUTES -----------------

@app.get("/api/conversations")
def get_conversations():
    return list(conversations_db.values())

@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str):
    if conv_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversations_db[conv_id]

@app.get("/api/appointments")
def get_appointments():
    return appointments_db

@app.post("/api/simulate")
def simulate_message(req: SimulateMessageRequest):
    global conversations_db, appointments_db
    
    # Generate structured conversation ID based on name & channel
    conv_key = f"conv_{req.channel.lower().replace(' ', '_')}_{req.sender_name.lower().replace(' ', '_')}"
    
    # Create new conversation structure if not exists
    if conv_key not in conversations_db:
        conversations_db[conv_key] = {
            "id": conv_key,
            "name": req.sender_name,
            "channel": req.channel,
            "contact": req.sender_contact,
            "unread_count": 0,
            "status": "Pending",
            "messages": [],
            "lead_profile": {
                "lead_name": req.sender_name,
                "lead_email": "N/A",
                "lead_phone": "N/A",
                "lead_company": "N/A",
                "lead_interest": "N/A",
                "lead_sentiment": "Neutral",
                "lead_score": 50,
                "ai_summary": "Simulated active lead. Awaiting analysis."
            }
        }
    
    conv = conversations_db[conv_key]
    
    # 1. Append User Message
    conv["messages"].append({
        "sender": "user",
        "text": req.message,
        "timestamp": get_timestamp()
    })
    
    # If in Human Takeover mode, we don't auto-reply, just set unread count
    if conv["status"] == "Human Takeover":
        conv["unread_count"] += 1
        return conv
        
    # 2. Get AI Auto-reply
    ai_reply_text = get_gemini_reply(req.channel, req.message, conv["messages"])
    
    # 3. Append AI Reply
    conv["messages"].append({
        "sender": "ai",
        "text": ai_reply_text,
        "timestamp": get_timestamp()
    })
    conv["status"] = "AI Replied"
    
    # 4. Extract and update lead profile
    updated_profile = extract_lead_profile(req.sender_name, req.sender_contact, conv["messages"])
    conv["lead_profile"].update(updated_profile)
    
    # 5. Dynamic Calendar Booking Hooks (Differentiator!)
    message_lower = req.message.lower()
    if "book" in message_lower or "demo" in message_lower or "appointment" in message_lower:
        time_slot = "Tomorrow at 3:00 PM IST"
        if "tomorrow" in message_lower:
            time_slot = "Tomorrow at 3:00 PM IST"
        elif "friday" in message_lower:
            time_slot = "Friday at 11:00 AM IST"
        elif "wednesday" in message_lower:
            time_slot = "Wednesday at 10:00 AM IST"
            
        existing = any(a["name"] == req.sender_name and a["datetime"] == time_slot for a in appointments_db)
        if not existing:
            appointments_db.append({
                "id": f"apt_{int(time.time())}",
                "name": req.sender_name,
                "datetime": time_slot,
                "channel": req.channel
            })
    
    # Capture lead to simulated Google Sheets if connected
    if google_sheets_connected:
        logger.info(f"💾 [GOOGLE SHEETS] Successfully exported lead '{req.sender_name}' to target sheet.")
        
    return conv

@app.post("/api/reply")
def reply_manually(req: ReplyRequest):
    if req.conv_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    conv = conversations_db[req.conv_id]
    
    # Append human message
    conv["messages"].append({
        "sender": "human",
        "text": req.text,
        "timestamp": get_timestamp()
    })
    
    # Force Human Takeover status
    conv["status"] = "Human Takeover"
    conv["unread_count"] = 0
    
    # Re-extract profile to see if new manually collected data changes things
    updated_profile = extract_lead_profile(conv["name"], conv["contact"], conv["messages"])
    conv["lead_profile"].update(updated_profile)
    
    return conv

@app.post("/api/takeover")
def toggle_takeover(req: Dict[str, Any]):
    conv_id = req.get("conv_id")
    if conv_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    conv = conversations_db[conv_id]
    current_status = conv["status"]
    
    if current_status == "Human Takeover":
        conv["status"] = "AI Replied"
    else:
        conv["status"] = "Human Takeover"
        
    return {"status": conv["status"]}

@app.get("/api/owner-settings")
def get_owner_settings():
    return owner_settings

@app.post("/api/owner-settings")
def update_owner_settings(req: OwnerSettingsRequest):
    global owner_settings
    owner_settings["business_name"] = req.business_name
    owner_settings["whatsapp"] = req.whatsapp
    owner_settings["instagram"] = req.instagram
    owner_settings["email"] = req.email
    owner_settings["voice"] = req.voice
    
    logger.info(f"Updated Owner Business configuration settings: {owner_settings}")
    return {"success": True, "settings": owner_settings}

@app.post("/api/upload-rag")
def upload_rag_knowledge(req: RagUploadRequest):
    update_rag_store(req.content)
    return {"success": True, "message": "Knowledge base updated. AI will now use this context."}

@app.post("/api/upload-file")
async def upload_document_file(file: UploadFile = File(...)):
    try:
        content_bytes = await file.read()
        
        # Check if file is a PDF
        if file.filename.endswith(".pdf") and PDF_PARSING_AVAILABLE:
            pdf_reader = PdfReader(io.BytesIO(content_bytes))
            text_pages = []
            for page in pdf_reader.pages:
                text_pages.append(page.extract_text() or "")
            content = "\n".join(text_pages)
        else:
            # Standard Text
            content = content_bytes.decode("utf-8", errors="ignore")
            
        update_rag_store(content)
        logger.info(f"📚 RAG Knowledge Base successfully populated via upload! Chunks: {len(rag_chunks)}, chars: {len(content)}")
        return {"success": True, "chars": len(content), "filename": file.filename, "chunks": len(rag_chunks)}
    except Exception as e:
        logger.error(f"Failed to parse file upload: {e}")
        raise HTTPException(status_code=500, detail="Could not parse uploaded document or PDF.")

@app.post("/api/google-sheets-toggle")
def toggle_sheets():
    global google_sheets_connected
    google_sheets_connected = not google_sheets_connected
    return {"sheets_connected": google_sheets_connected}

@app.get("/api/stats")
def get_stats():
    # Calculate real stats from current in-memory database
    total_leads = len(conversations_db)
    ai_replied = sum(1 for c in conversations_db.values() if c["status"] == "AI Replied")
    takeover_count = sum(1 for c in conversations_db.values() if c["status"] == "Human Takeover")
    
    ai_reply_rate = int((ai_replied / total_leads * 100)) if total_leads > 0 else 100
    
    # Score metrics
    scores = [c["lead_profile"]["lead_score"] for c in conversations_db.values()]
    avg_score = int(sum(scores) / len(scores)) if scores else 0
    
    # Sentiment count
    sentiments = [c["lead_profile"]["lead_sentiment"] for c in conversations_db.values()]
    pos = sentiments.count("Positive")
    neu = sentiments.count("Neutral")
    neg = sentiments.count("Negative")
    
    # Channel distribution
    channels = [c["channel"] for c in conversations_db.values()]
    channel_data = []
    unique_channels = list(set(channels))
    for chan in unique_channels:
        channel_data.append({
            "channel": chan,
            "count": channels.count(chan)
        })
        
    return {
        "total_leads": total_leads,
        "ai_reply_rate": ai_reply_rate,
        "takeover_count": takeover_count,
        "avg_score": avg_score,
        "sentiment": {"Positive": pos, "Neutral": neu, "Negative": neg},
        "channels": channel_data,
        "gemini_active": GEMINI_AVAILABLE
    }

# Serving index.html directly
@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    raise HTTPException(status_code=404, detail="Index page static file missing.")

# Mount other static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
