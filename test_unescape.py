from sanitizer import sanitize_response

test_input = 'There are 3 \\"r\\"s in the word strawberry.\\n\\nHere is the breakdown:\\nstrawberry'
expected_output = 'There are 3 "r"s in the word strawberry.\n\nHere is the breakdown:\nstrawberry'

cleaned = sanitize_response(test_input)

print("--- INPUT ---")
print(test_input)
print("\n--- CLEANED ---")
print(cleaned)
print("\n--- EXPECTED ---")
print(expected_output)

if cleaned == expected_output:
    print("\n✅ SUCCESS: Text was correctly unescaped.")
else:
    print("\n❌ FAILURE: Output does not match expected.")
    print(f"Got: {repr(cleaned)}")
