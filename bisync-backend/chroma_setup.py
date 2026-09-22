import chromadb

# Local persistent client connect kar rahe hain
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="bis_rulebook")

# 1. Sample BIS Standards aur Clauses add karte hain
sample_bis_rules = [
    "IS 4151: Protective helmets for motorcycle riders must have durable outer shell, EPS liner, and clear ISI mark.",
    "IS 14543: Packaged drinking water must mention batch number, expiry date, FSSAI license, and CM/L BIS license code.",
    "IS 694: PVC insulated cables for working voltages up to 1100V must clearly bear brand name, voltage grade, and ISI logo.",
    "IS 1293: Plugs, socket-outlets, and adapters for household and similar purposes safety standards.",
    "IS 16102 (Part 1): Self-ballasted LED lamps for general lighting services requirements.",
    "IS 302-2-3: Electric irons for household use safety specifications.",
    "IS 302-2-201: Electric immersion water heaters safety standards.",
    "IS 13250: Safety of information technology equipment and mobile chargers/adapters.",
    "IS 3854: Switches for household and similar fixed electrical installations.",
    "IS 15652: Insulating mats for electrical purposes.",
    "Clause 4.2: Any product without valid CM/L 7-digit registration number cannot legally claim BIS compliance."
]

rule_ids = [
    "rule_helmet", 
    "rule_water", 
    "rule_cable", 
    "rule_plug", 
    "rule_led", 
    "rule_iron", 
    "rule_heater", 
    "rule_charger", 
    "rule_switch", 
    "rule_mat", 
    "rule_clause_4_2"
]

# Data ko vector database mein store karte hain (embeddings automatically banengi)
collection.upsert(
    documents=sample_bis_rules,
    ids=rule_ids
)

print("Sample BIS Rules successfully indexed into ChromaDB!\n")