import os
import chromadb
from PyPDF2 import PdfReader

# ==========================================
# 1. DATABASE & COLLECTION SETUP
# ==========================================
CHROMA_PATH = "./chroma_store"
# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# Create or connect to the existing rulebook collection
rulebook = chroma_client.get_or_create_collection(name="bis_rulebook")

# ==========================================
# 2. PDF CHUNKING & INGESTION FUNCTION
# ==========================================
def ingest_pdf(file_path, standard_name, product_category):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        
        # Simple text chunking logic (approx 1000 characters per chunk with overlap)
        chunk_size = 1000
        overlap = 100
        chunks = []
        
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i+chunk_size])
        
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            if chunk.strip():  # Skip empty chunks
                documents.append(chunk)
                metadatas.append({"source": standard_name, "category": product_category})
                ids.append(f"{standard_name.replace(' ', '_')}_chunk_{i}")
        
        if documents:
            rulebook.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"✅ Successfully embedded {len(documents)} chunks for {standard_name} into ChromaDB!")
        else:
            print(f"⚠️ No text could be extracted from {file_path}")
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {str(e)}")

# ==========================================
# 3. MAIN EXECUTION BLOCK (RUN ALL PDFS)
# ==========================================
if __name__ == "__main__":
    print(f"📦 Initial documents in ChromaDB: {rulebook.count()}")

    # 1. Simplified Procedure
    pdf_1 = "pdfs/List-of-Products-Under-Simplified-Procedure.pdf"
    if os.path.exists(pdf_1):
        print(f"\nReading {pdf_1}...")
        ingest_pdf(
            file_path=pdf_1,
            standard_name="BIS Simplified Procedure Scheme-II",
            product_category="Multiple MSME & Domestic Products"
        )
    else:
        print(f"❌ File not found: {pdf_1}")

    # 2. BIS Recognized Labs Directory
    pdf_2 = "pdfs/Group_1_24062026.pdf"
    if os.path.exists(pdf_2):
        print(f"\nReading {pdf_2}...")
        ingest_pdf(
            file_path=pdf_2,
            standard_name="List of BIS Recognized Laboratories",
            product_category="Testing Laboratories Directory"
        )
    else:
        print(f"❌ File not found: {pdf_2}")

    # 3. Hallmarking Scheme Overview
    pdf_3 = "pdfs/brief-on-Hallmarking.pdf"
    if os.path.exists(pdf_3):
        print(f"\nReading {pdf_3}...")
        ingest_pdf(
            file_path=pdf_3,
            standard_name="Brief on Hallmarking Scheme",
            product_category="Gold & Silver Hallmarking Basics"
        )
    else:
        print(f"❌ File not found: {pdf_3}")

    # 4. Hallmarking Guidelines for Jewellers
    pdf_4 = "pdfs/Guidelines-for-Jewellers.pdf"
    if os.path.exists(pdf_4):
        print(f"\nReading {pdf_4}...")
        ingest_pdf(
            file_path=pdf_4,
            standard_name="Guidelines for Jewellers",
            product_category="Hallmarking Compliance & Market Surveillance"
        )
    else:
        print(f"❌ File not found: {pdf_4}")

    print(f"\n🚀 Final documents in ChromaDB: {rulebook.count()}")