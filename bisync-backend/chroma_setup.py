import chromadb

# Local persistent client connect kar rahe hain
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="bis_rulebook")

# 1. Sample BIS Standards aur Clauses add karte hain
sample_bis_rules = [
    "IS 4151: Protective helmets for motorcycle riders must have durable outer shell, EPS liner, and clear ISI mark.",
    "IS 14543: Packaged drinking water must mention batch number, expiry date, FSSAI license, and CM/L BIS license code.",
    "IS 694: PVC insulated cables for working voltages up to 1100V must clearly bear brand name, voltage grade, and ISI logo.",
    "Clause 4.2: Any product without valid CM/L 7-digit registration number cannot legally claim BIS compliance."
]

rule_ids = ["rule_helmet", "rule_water", "rule_cable", "rule_clause_4_2"]

# Data ko vector database mein store karte hain (embeddings automatically banengi)
collection.upsert(
    documents=sample_bis_rules,
    ids=rule_ids
)

print("Sample BIS Rules successfully indexed into ChromaDB!\n")

# 2. Test semantic query: bina exact keyword ke AI search check karte hain
user_query = "What are the rules for biker safety helmets?"
print(f"Testing Query: '{user_query}'")

results = collection.query(
    query_texts=[user_query],
    n_results=1
)

print("\nAI Search Match:")
print(f"Matched Rule: {results['documents'][0][0]}")
print(f"Matched ID: {results['ids'][0][0]}")