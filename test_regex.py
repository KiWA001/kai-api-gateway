
import re

# User's exact example (Step 1116)
# Note: JSON string had \n escaped. Python string formatting:
user_example = """Thought Process
Considering the user's simple greeting, I need to respond with an appropriate friendly opening. A warm welcome is essential, so I'll start with "Hello!" as it sets a positive tone. Given my role as a GLM language model trained by Z.ai, I should introduce my purpose: being a helpful assistant capable of answering diverse questions. Including a prompt for their needs next would encourage engagement, like asking "How can I assist you today?" This matches my identity and keeps the interaction open-ended for their response. I'll maintain a cheerful and professional demeanor throughout to build rapport.
Hello! I'm GLM, a large language model trained by Z.ai. I'm here to assist with information, answer questions, or just chat about topics that interest you.
How can I help you today? Whether you need information, creative ideas, or just want to have a conversation, I'm happy to engage."""

# My previous example (double newline)
double_newline_example = """Thought Process

The user said "hi there".
This is a simple greeting.

Hello! How can I help you today?"""

def test_clean(text, name):
    print(f"--- {name} ---")
    # Regex Strategy:
    # Match "Thought Process" at start.
    # Match any content (non-greedy) including newlines.
    # Stop at the last newline before the Answer?
    
    # User said: "remove all the way to the forward slash n"
    # This implies there is a newline separating Thoughts and Answer.
    
    # Attempt 1: Remove `Thought Process` + `\s+` + `Content` + `\n`
    # How do we know what is content vs answer?
    # Heuristic: Answer usually starts with Hello, Yes, The, etc.
    # Thoughts are usually "Considering...", "Analysis:".
    
    # What if we just split by first newline that matches a Lookahead?
    # No.
    
    # If the text starts with "Thought Process", we assume the FIRST chunk is thoughts.
    # If there is a newline, we split on it.
    
    # Let's try splitting by `\n`.
    parts = text.split('\n')
    # Use index 0: "Thought Process".
    # Index 1: "Considering..." (The thought body).
    # Index 2: "Hello! ..." (The answer).
    
    # So for User Example:
    # we want to drop parts[0] and parts[1].
    # Return parts[2:].
    
    # For Double Newline Example:
    # "Thought Process"
    # ""
    # "The user said..."
    # "This is..."
    # ""
    # "Hello!..."
    
    # This looks like we want to drop up to the last empty string?
    
    # Revised Logic based on User Feedback:
    # "Remove the whole thought process all the way to the forward slash n"
    # This assumes the thought process is ONE block followed by \n.
    
    clean = text.strip()
    
    if clean.startswith("Thought Process"):
        # Find the split point.
        # If we assume Thought Process is the Header.
        # And the Next line is the Body.
        # And the Next line is the Answer.
        
        # Regex: `^Thought Process\s*\n.*?\n` matches Header + Body + Newline.
        # Result should be Answer.
        
        # NOTE: `.` does not match `\n` unless DOTALL.
        # But `.*?\n` finds the *first* newline after matching start?
        # "Considering ... rapport.\n" -> Match!
        
        # Let's try this specific regex.
        # Matches "Thought Process" + optional whitespace/newlines + content + newline.
        # Non-greedy `.*?` ensures we stop at the FIRST newline after the content begins?
        # Wait, "Thinking contents" might be multiline.
        
        # Let's try: Remove everything up to the first occurrence of `\n(?=[A-Z])`?
        
        # Simple Logic:
        # If single-newline separator (User example):
        # We want to remove the first 2 lines?
        # "Thought Process" (1)
        # "Considering..." (2)
        # Answer (3)
        
        # Let's try Regex: `r"^Thought Process.*?(\n\n|\n)(?=[A-Z])"`?
        # Using DOTALL for content.
        
        cleaned = re.sub(r"^Thought Process.*?\n(?=[A-Z])", "", clean, flags=re.DOTALL | re.MULTILINE).strip()
        print(f"REGEX OUTPUT:\n{cleaned}\n")
        return cleaned

    return clean

test_clean(user_example, "User Example")
test_clean(double_newline_example, "Double Line Example")
