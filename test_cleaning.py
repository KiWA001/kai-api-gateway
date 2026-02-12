
import re

# New Headerless Example (Step 1171)
headerless_example = """Let me consider how to respond to this greeting effectively.
The user has initiated contact with a simple "hi there" - this suggests they're starting a conversation but haven't specified their needs yet. A warm, professional response would be most appropriate here.
The key is to strike the right balance between being approachable and professional. I'll extend a friendly greeting back and offer assistance, leaving the door open for them to share what they need help with. This establishes a positive tone for our interaction while giving them the space to direct the conversation.
Let me formulate a response that's welcoming yet professional, and invites them to specify how I can assist them today.
Hi there! I'm the GLM language model trained by Z.ai. How can I assist you today? Whether you have questions, need information, or just want to chat, I'm here to help. What would you like to discuss?"""

# Previous Valid Example (Standard)
header_example = """Thought Process

The user said hi.
I need to reply.

Hello! How are you?"""

# Multi-paragraph Answer (Edge Case for "Last \n" rule)
multi_para_answer = """Thinking...
Skipped.

Yes, I can help with that.

Here is a list of items:
1. Item one
2. Item two

End of list."""

def clean_response(text):
    print(f"--- Original ({len(text)} chars) ---\n{text}\n----------------")
    
    clean = text.strip()
    # Remove UI artifacts
    clean = re.sub(r"^(Thinking\.\.\.|Skip|\s)+", "", clean, flags=re.MULTILINE).strip()
    
    # Split blocks (try double newline first, then single if consistent)
    # The headerless example uses single newlines.
    
    # Strategy:
    # 1. Detect if "thoughts" are present.
    #    - Look for "Thought Process" header.
    #    - Look for "Let me consider", "The user has", "I need to".
    
    has_header = "thought process" in clean.lower()[:50]
    
    # Heuristic keywords for headerless thoughts
    thought_indicators = [
        "let me consider",
        "the user has",
        "the user said",
        "i need to",
        "i'll extend",
        "i will",
        "let me formulate",
        "analysis:",
    ]
    
    has_thought_indicators = False
    # Check the first 200 chars?
    intro = clean.lower()[:300]
    for ind in thought_indicators:
        if ind in intro:
            has_thought_indicators = True
            break
            
    if not has_header and not has_thought_indicators:
        # If clean, return as is (don't apply aggressive "last paragraph" rule)
        # This protects "Multi-paragraph Answer"
        print("DEBUG: Clean response detected.")
        return clean
        
    # If we detect thoughts...
    
    # User Request: "remove everything before the last \n"
    # This implies taking the LAST block.
    
    # Let's split by newline.
    blocks = clean.split('\n')
    # Filter empty
    blocks = [b.strip() for b in blocks if b.strip()]
    
    # The user's rule ("Last \n") maps to returning blocks[-1].
    # But checking if blocks[-1] is just "End of list."?
    # In the headerless example, the answer consists of ONE paragraph at the end.
    
    # If we apply "Return Last Block" to headerless_example:
    # It returns: "Hi there! ..." -> CORRECT.
    
    # If we apply to header_example:
    # It returns: "Hello! How are you?" -> CORRECT.
    
    # If we apply to multi_para_answer (assuming it has NO indicators):
    # It enters the "Clean response" branch -> CORRECT.
    
    # What if a Thought Response HAS indicators but ALSO a multi-paragraph answer?
    # e.g. "Let me consider.\n\nHello!\n\nHere is a list..."
    # If we return LAST block, we lose "Hello!".
    
    # We need to find the SPLIT point.
    # Iterate from end?
    # Or iterate from start and drop blocks that look like thoughts?
    
    filtered_blocks = []
    # If we established there ARE thoughts, we interpret the first few blocks as garbage.
    
    # In headerless example, blocks 0, 1, 2, 3 are thoughts. Block 4 is answer.
    # All 0-3 contain "Let me", "The user", "I'll", "Let me".
    
    # Safe logic: Drop blocks from start as long as they contain indicators?
    # Or strict "Last Paragraph" as user requested?
    # User said: "try to remove everything before the last \n"
    # I will strictly follow this for now, IF indicators are present.
    # Because Z.ai usually outputs thoughts then ONE final answer block.
    
    if len(blocks) > 1:
        # Check if we should be aggressive
        if has_header or has_thought_indicators:
             # Logic: Return the text AFTER the last newline separator of the thoughts.
             # If we just return blocks[-1], we are safe for Z.ai 90% of time.
             print("DEBUG: Applying Aggressive Last Block strategy.")
             return blocks[-1]
             
    return clean

print("--- TEST 1 (Headerless) ---")
c1 = clean_response(headerless_example)
print(f"CLEANED:\n{c1}\n")

print("--- TEST 2 (Multi-Para Clean) ---")
c2 = clean_response(multi_para_answer)
print(f"CLEANED:\n{c2}\n")
