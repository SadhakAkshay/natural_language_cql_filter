import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser,JsonOutputParser

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.2
)

prompt = PromptTemplate(
    template="""
You are given a JSON representing PostgreSQL schema metadata 
(from information_schema.columns).

The JSON contains:
- table_name
- table_schema
- column_name
- data_type

Task:
Generate a text document where:

1. Each table is described in a single well-written paragraph.
2. Mention all its columns.
3. Provide a short meaningful description for each column.
4. Also describe the exact geometry type of the table also from the geom column which we 
have stored as the key geom_type within json.
4. Keep formatting clean and professional.
5. Maintain uniqueness in column descriptions.
6. Do not repeat tables.

JSON:
{json_file}
""",
    input_variables=["json_file"]
)

prompt = PromptTemplate(
    template="""
You are given a JSON representing PostgreSQL schema metadata 
(from information_schema.columns).

The JSON contains:
- table_name
- table_schema
- column_name
- data_type
- geom_type (geometry type of the table derived from the geom column)

Task:
Generate a clean, professional text document where:

1. Each table is described in a single well-written paragraph.
2. Clearly mention the table schema and table name.
3. Mention all columns belonging to the table.
4. Provide a short, meaningful, and unique description for each column.
5. If the table contains a geometry column:
   - Use the value of "geom_type" from the JSON.
   - Clearly state the exact geometry type (e.g., POINT, LINESTRING, POLYGON, MULTIPOLYGON).
   - Explain briefly what that geometry type represents spatially.
6. Do not hallucinate geometry types. Only use the provided "geom_type".
7. Do not repeat tables.
8. Maintain professional documentation style.

JSON:
{json_file}
""",
    input_variables=["json_file"]
)

parser=StrOutputParser()

chain = prompt | llm | parser

import json

with open("postgres_schema_metadata.json", "r") as f:
    schema_json = json.load(f)

schema_str = json.dumps(schema_json, indent=2)

result = chain.invoke({"json_file": schema_str})

output_file_path = "database_schema_documentation_for_sld.txt"

with open(output_file_path, "w", encoding="utf-8") as file:
    file.write(result)

print(f"Documentation saved successfully at: {os.path.abspath(output_file_path)}")


#second type where here we will fetch the table name , associated column name and probable attribute value




# result3 = []

# for item, condition in zip(result2, result1['extracted_conditions']):
#     result3.append({
#         'table_name': 'hospitals_in_india',
#         'column_name': item['column'],
#         'operator': condition['possible_operator'],
#         'value': condition['attribute_value']
#     })

# result3.append({'logical_operator': result1['overall_logical_operator']})

# print(222222222222222222222)
# print(result3)

# #HERE COMES THE THIRD STAGE WHERE WE ARE FORMULATING THE FINAL OUTPUT AS PER THE STANDARD CQL
# #  result=[{'table_name': 'india_state_boundary', 'column_name': 'state_name', 
# #  'operator': '=', 'value': 'kerala'}, {'table_name': 'india_state_boundary', 
# #  'column_name': 'state_name', 'operator': '=', 'value': 'panjab'}, {'logical_operator': 'OR'}]

# # result3=[{'table_name': 'hospitals_in_india', 'column_name': 'city', 'operator': '=', 
# # 'value': 'nashik'}, {'table_name': 'hospitals_in_india', 'column_name': 'density', 
# # 'operator': '<', 'value': '300'}, {'logical_operator': 'AND'}]

# from collections import Counter

# import psycopg2

# conn = psycopg2.connect(
#     database="postgres", user='postgres',
#     password='postgres', host='localhost', port='5432'
# )

# conn.autocommit = True
# cursor = conn.cursor()

# key_to_count='column_name'
# counts = {}
# table_name1=''

# def get_value_by_condition(data_list, condition_key, condition_value, target_key):
#     for d in data_list:
#         if d.get(condition_key) == condition_value:
#             return d.get(target_key)
#     return None

# for i in result3:
#     if 'table_name' in i:
#         if key_to_count in i:
#           value = i[key_to_count]
#           counts[value] = counts.get(value, 0) + 1

#     else:
#         print(i['logical_operator'])
  
# schema_name='dynamic_sld'
# result_string = ''
# final_result_string=''

# for key, value in counts.items():
#     if value > 1:
#         #print("Duplicate found for:", key)

#         table_name1 = get_value_by_condition(
#             result3, 'column_name', key, 'table_name'
#         )

#         sql = f"""
#         select data_type 
#         from information_schema.columns 
#         where column_name = '{key}' 
#         and table_name = '{table_name1}';
#         """

#         print(3333333333333333)
#         print(sql)
#         cursor.execute(sql)
#         column_type = cursor.fetchall()

#         column_key = key

#         filtered_values = [
#             d['value']
#             for d in result3
#             if d.get('column_name') == column_key
#         ]

        
#         type_of_column = column_type[0][0]

#         for i, value in enumerate(filtered_values):

#             if type_of_column == 'character varying' or type_of_column == 'text':

#                 value_sql = f"""
#                 select {key} 
#                 from {schema_name}.{table_name1} 
#                 where {key} ilike '%{value}%' 
#                 limit 1;
#                 """

#                 cursor.execute(value_sql)
#                 values = cursor.fetchall()

#                 if values and i != len(filtered_values) - 1:
#                     if result_string=='':
#                       result_string += "'" + values[0][0] + "',"
#                     else:
#                       result_string += ",'" + values[0][0] + "',"
#                 elif values and i == len(filtered_values) - 1:
#                     result_string += "'" + values[0][0] + "'"

#             else:

#                 value_sql = f"""
#                 select {key} 
#                 from {schema_name}.{table_name1} 
#                 where {key} = {value} 
#                 limit 1;
#                 """

#                 cursor.execute(value_sql)
#                 values = cursor.fetchall()

#                 if values and i != len(filtered_values) - 1:
#                     result_string += str(values[0][0]) + ","
#                 elif values and i == len(filtered_values) - 1:
#                     result_string += str(values[0][0])

#         if result_string.endswith(","):
#             result_string = result_string[:-1]
        
#         if(final_result_string=='' and i != len(filtered_values) - 1):
#           final_result_string=result_string + i['logical_operator']   
#         elif(final_result_string=='' and i == len(filtered_values) - 1):
#           final_result_string=result_string
#         elif(final_result_string!=''):
#           final_result_string= i['logical_operator']  + result_string 

#     else:
#         print('go from here')
#         print(key)
#         print(value)

#         table_name1 = get_value_by_condition(
#             result3, 'column_name', key, 'table_name'
#         )

#         sql = f"""
#         select data_type 
#         from information_schema.columns 
#         where column_name = '{key}' 
#         and table_name = '{table_name1}';
#         """

#         print(3333333333333333)
#         print(sql)
#         cursor.execute(sql)
#         column_type = cursor.fetchall()

#         column_key = key

#         filtered_values = [
#             d['value']
#             for d in result3
#             if d.get('column_name') == column_key
#         ]

        
#         type_of_column = column_type[0][0]

#         for i, value in enumerate(filtered_values):

#             if type_of_column == 'character varying' or type_of_column == 'text':

#                 value_sql = f"""
#                 select {key} 
#                 from {schema_name}.{table_name1} 
#                 where {key} ilike '%{value}%' 
#                 limit 1;
#                 """

#                 cursor.execute(value_sql)
#                 values = cursor.fetchall()

#                 found_object = next((result for result in result3 if result['column_name'] == key), None)
#                 print(found_object)
#                 result_string +=  ","+key+found_object['operator']+"'" + values[0][0] + "'"

#             else:

#                 value_sql = f"""
#                 select {key} 
#                 from {schema_name}.{table_name1} 
#                 where {key} = {value} 
#                 limit 1;
#                 """

#                 cursor.execute(value_sql)
#                 values = cursor.fetchall()

#                 found_object = next((result for result in result3 if result['column_name'] == key), None)
#                 print(found_object)
#                 result_string += ","+key+found_object['operator']+values[0][0]

# if result_string.startswith(","):
#   result_string = result_string[:-1]

# print(result_string)
# conn.commit()
# conn.close()