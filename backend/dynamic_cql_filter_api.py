from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import re
import psycopg2
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel as PydanticBase
from dotenv import load_dotenv

language = APIRouter()
load_dotenv()
# Initialize LLM
llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.2,
    groq_api_key=os.getenv("groq_api_key")
)

# DB connection
conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="postgres"
)

# Request model
class QueryRequest(BaseModel):
    table_name: str
    text: str

# Load schema once at startup
with open("database_schema_documentation_for_sld.txt", "r", encoding="utf-8") as f:
    schema_text = f.read()

# Prompts
prompt1 = PromptTemplate(
    template="""
You are a natural language condition extraction engine.

You are given a user sentence:

"{sentence}"

Your task:

STEP 1:
Extract all distinct attribute VALUES mentioned in the sentence.
- These may be names, numbers, locations, categories, etc.
- Do NOT infer database column names.
- Do NOT map values to schema.
- Only extract literal values explicitly present in the sentence.

STEP 2:
For each extracted value, determine the possible comparison operator.

Allowed operators:
=, !=, >, <, >=, <=

Rules:
- If no comparison word is present, default operator is "=".
- If words like "greater than", "more than" → use ">"
- If words like "less than", "below" → use "<"
- If words like "not equal", "except" → use "!="

STEP 3:
Detect overall logical operator between conditions.
- If sentence implies conjunction → "AND"
- If sentence implies alternative → "OR"
- If only one condition → return "NONE"

STRICT OUTPUT RULES:

- Return ONLY valid JSON.
- Do NOT include explanations.
- Do NOT wrap in markdown.
- Do NOT add extra text before or after JSON.
- First character must be '{{'
- Last character must be '}}'

Output format must be:

{{
  "extracted_conditions": [
    {{
      "attribute_value": "value_from_sentence",
      "possible_operator": "="
    }}
  ],
  "overall_logical_operator": "AND"
}}

If no values are found, return:

{{
  "extracted_conditions": [],
  "overall_logical_operator": "NONE"
}}
""",
    input_variables=["sentence"]
)

prompt2 = PromptTemplate(
    template="""
You are a database schema analysis engine.

You are given:

1) Database schema documentation text:
\"\"\"
{schema_text}
\"\"\"

2) Target table name:
{table_name}

3)  Probable values (one per line)::
{value_list}

Your task:

STEP 1:
Carefully analyze the schema documentation.
Locate the table that exactly matches the provided table name.
Extract ONLY the columns that belong to that specific table.
Ignore all other tables.

STEP 2:
For each value in the provided value list:
- Determine which column from the identified table can logically contain that value.
- Only use column names that explicitly appear under the specified table in the schema documentation.
- Do NOT use columns from other tables.
- Do NOT invent column names.
- Do NOT assume undocumented columns.
- Match based strictly on semantic meaning and datatype compatibility.

STEP 3:
If:
- A clear matching column exists in the specified table → return that column name.
- Multiple columns seem possible → return the most semantically accurate one.
- No suitable column exists in that table → return null.

STRICT OUTPUT RULES:

- Return ONLY valid JSON.
- Do NOT include explanations.
- Do NOT wrap in markdown.
- Do NOT add extra text before or after JSON.
- First character must be '['
- Last character must be ']'

Output format must be:

[
  {{
    "value": "value_from_list",
    "column": "matched_column_name_or_null"
  }}
]

If value_list is empty, return:

[]
""",
    input_variables=["schema_text", "table_name", "value_list"]
)

tree_prompt = PromptTemplate(
    input_variables=["user_query", "flat_conditions"],
    template="""
You are a logical query tree generator.

You are given:

1. A natural language database query.
2. A list of extracted flat filter conditions from a PostgreSQL table.

Your task:
Transform the flat conditions into a nested logical tree structure
using ONLY the provided conditions.

Important Rules:
- DO NOT create new columns.
- DO NOT modify operators or values.
- ONLY group the given conditions.
- Use "AND" and "OR" operators.
- Support nesting when required.
- Return strictly valid JSON.
- No explanation. Only JSON.

Tree Format:

{{
  "operator": "AND | OR",
  "conditions": [
      {{
        "operator": "AND | OR",
        "conditions": [ ... nested nodes ... ]
      }},
      {{
        "column_name": "...",
        "operator": "...",
        "value": "..."
      }}
  ]
}}

Natural Language Query:
{user_query}

Flat Conditions:
{flat_conditions}

Generate the logical tree now:
"""
)

chain1 = prompt1 | llm | JsonOutputParser()
chain2 = prompt2 | llm | JsonOutputParser()
chain3 = tree_prompt | llm | JsonOutputParser()


def clean_value(value):
    return re.sub(r'^\d+\.\s*', '', value)


def get_column_type(cursor, table_name, column_name):
    query = """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = %s
        AND column_name = %s
        LIMIT 1
    """
    cursor.execute(query, (table_name, column_name))
    result = cursor.fetchone()
    return result[0] if result else None


def get_actual_value(cursor, table_name, column, value, column_type):
    def execute_query(search_value, use_ilike=True):
        if use_ilike:
            query = f"""
                SELECT {column}
                FROM dynamic_sld.{table_name}
                WHERE {column} ILIKE %s
                LIMIT 1
            """
            cursor.execute(query, (f"%{search_value}%",))
        else:
            query = f"""
                SELECT {column}
                FROM dynamic_sld.{table_name}
                WHERE {column} = %s
                LIMIT 1
            """
            cursor.execute(query, (search_value,))
        return cursor.fetchone()

    # If text column → use fallback matching
    if column_type in ('character varying', 'text', 'varchar'):

        # 1️⃣ Try full value
        result = execute_query(value)
        if result:
            return result[0]

        # 2️⃣ Try first 3 characters
        if len(value) >= 3:
            first_three = value[:3]
            result = execute_query(first_three)
            if result:
                return result[0]

        # 3️⃣ Try last 3 characters
        if len(value) >= 3:
            last_three = value[-3:]
            result = execute_query(last_three)
            if result:
                return result[0]

        return None

    else:
        # For non-text columns → exact match only
        result = execute_query(value, use_ilike=False)
        return result[0] if result else None


def replace_values_with_db_values(table_name, filters):
    updated_filters = []
    with conn.cursor() as cursor:
        for item in filters:
            column = item['column']
            raw_value = item['value']
            cleaned_value = clean_value(raw_value)
            column_type = get_column_type(cursor, table_name, column)

            if not column_type:
                updated_filters.append({'column': column, 'value': 'not_available_here'})
                continue

            actual_value = get_actual_value(cursor, table_name, column, cleaned_value, column_type)
            if actual_value is not None:
                updated_filters.append({'column': column, 'value': actual_value})
            else:
                updated_filters.append({'column': column, 'value': 'not_available_here'})

    return updated_filters


def build_sql(node):
    if "conditions" in node:
        operator = node["operator"]
        parts = [build_sql(child) for child in node["conditions"]]
        return "(" + f" {operator} ".join(parts) + ")"
    column = node["column_name"]
    operator = node["operator"]
    value = node["value"]
    if isinstance(value, str):
        return f"{column} {operator} '{value}'"
    else:
        return f"{column} {operator} {value}"


@language.post("/generate-sql")
async def generate_sql(request: QueryRequest):
    try:
        # Step 1: Extract conditions from text
        result1 = chain1.invoke({"sentence": request.text})
        conditions = result1.get('extracted_conditions', [])
        attribute_values = [c.get('attribute_value') for c in conditions]
        formatted_values = "\n".join([f"{i+1}. {v}" for i, v in enumerate(attribute_values)])

        # Step 2: Map values to schema columns
        result2 = chain2.invoke({
            "schema_text": schema_text,
            "table_name": request.table_name,
            "value_list": formatted_values
        })

        # Step 3: Replace with actual DB values
        newresult = replace_values_with_db_values(request.table_name, result2)

        # Step 4: Build logical tree
        result3 = chain3.invoke({
            "user_query": request.text,
            "flat_conditions": newresult
        })

        # Step 5: Generate SQL
        sql = build_sql(result3)
        return {"sql": sql}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))