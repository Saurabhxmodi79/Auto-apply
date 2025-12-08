# MCP Database Update Tools

These tools allow the LLM to learn from job applications and remember your answers for future use.

## Available Update Tools

### 1. `add_custom_answer`
**Use when:** A job application asks a question not covered in your profile.

**Parameters:**
- `email`: Your email address
- `question`: The exact question asked
- `answer`: Your answer to remember
- `category`: (optional) Category like 'work_authorization', 'relocation', 'salary', 'diversity', 'preferences'

**Example Scenario:**
```
Application asks: "Are you willing to work on weekends?"
LLM: "I don't have this information. Are you willing to work on weekends?"
You: "Yes, I'm flexible with weekend work"
LLM calls: add_custom_answer(
    email="Modisaurabh79@gmail.com",
    question="Are you willing to work on weekends?",
    answer="Yes, I'm flexible with weekend work",
    category="preferences"
)
```

---

### 2. `update_profile_field`
**Use when:** Need to update a simple field in your profile.

**Parameters:**
- `email`: Your email address
- `field_name`: Name of the field (e.g., 'location', 'phone', 'summary', 'github', 'linkedin', 'portfolio')
- `value`: New value

**Example:**
```
update_profile_field(
    email="Modisaurabh79@gmail.com",
    field_name="location",
    value="Mumbai, Maharashtra, India"
)
```

---

### 3. `add_skill`
**Use when:** Need to add a new skill not in your profile.

**Parameters:**
- `email`: Your email address
- `skill`: Skill name

**Example:**
```
add_skill(
    email="Modisaurabh79@gmail.com",
    skill="Kubernetes"
)
```

---

### 4. `add_language`
**Use when:** Need to add or update a language proficiency.

**Parameters:**
- `email`: Your email address
- `language`: Language name
- `proficiency`: Level ('Native', 'Fluent', 'Professional', 'Conversational', 'Basic')

**Example:**
```
add_language(
    email="Modisaurabh79@gmail.com",
    language="Hindi",
    proficiency="Native"
)
```

---

### 5. `get_custom_answers`
**Use when:** Want to retrieve previously saved custom answers.

**Parameters:**
- `email`: Your email address
- `category`: (optional) Filter by specific category

**Example:**
```
get_custom_answers(
    email="Modisaurabh79@gmail.com",
    category="work_authorization"
)
```

---

## Common Question Categories

Use these categories for `add_custom_answer`:

1. **work_authorization** - Visa status, work permits, sponsorship needs
2. **relocation** - Willingness to relocate, preferred locations
3. **salary** - Salary expectations, current salary
4. **diversity** - Gender, ethnicity, veteran status, disability
5. **preferences** - Work hours, remote preferences, travel willingness
6. **background** - Criminal background, credit check consent
7. **references** - Reference contacts, permission to contact
8. **availability** - Start date, notice period
9. **certifications** - Security clearances, professional licenses
10. **general** - Any other questions

---

## Workflow Example

**During Job Application:**

```
1. LLM encounters: "Do you require visa sponsorship?"
2. LLM checks profile → Not found
3. LLM checks custom_answers → Not found
4. LLM asks you: "Do you require visa sponsorship?"
5. You respond: "No, I have valid work authorization"
6. LLM calls: add_custom_answer(
       email="Modisaurabh79@gmail.com",
       question="Do you require visa sponsorship?",
       answer="No, I have valid work authorization",
       category="work_authorization"
   )
7. Next application with same question → LLM uses saved answer automatically!
```

---

## Testing the Tools

To test if the MCP server is working with the new tools:

1. **Restart Claude Desktop** (important!)
2. Start a new conversation
3. Try asking:
   ```
   Add a custom answer for me:
   Question: "Are you willing to relocate?"
   Answer: "Yes, I'm open to relocation within India"
   Category: "relocation"
   Email: Modisaurabh79@gmail.com
   ```

4. Then retrieve it:
   ```
   Get my custom answers for email Modisaurabh79@gmail.com
   ```

---

## Benefits

✅ **Learn as you go** - No need to pre-fill every possible question  
✅ **Reuse answers** - Same questions get answered automatically  
✅ **Organized by category** - Easy to review and update  
✅ **Timestamped** - Know when each answer was added  
✅ **No duplicates** - Skills and answers are stored uniquely  

---

## Notes

- All updates are immediate and permanent in MongoDB
- The MCP server must be restarted for tool changes to take effect
- Custom answers are stored with timestamps for tracking
- Skills use `$addToSet` to prevent duplicates automatically

