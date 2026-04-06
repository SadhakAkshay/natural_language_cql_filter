# 🗺️ NLP GIS Explorer — Natural Language WMS Layer Filter (GeoServer)

A full-stack GIS application that filters **GeoServer WMS layers** using plain English sentences. It leverages **Llama 3.3 70B** (via Groq) to understand natural language queries, extract relevant attributes and values from the layer schema, generate a valid **CQL filter**, and apply it directly to the WMS layer rendered via **OpenLayers**.

---

## ✨ What It Does

> _"Show me states where literacy rate is above 80%"_
> _"Give me all districts in Maharashtra with population greater than 500000"_
> _"Show highways and expressways in the road network"_

The system:
1. Identifies which attributes of the layer are relevant to the query
2. Extracts the correct values from the schema knowledge base
3. Generates a valid CQL filter string
4. Dynamically handles `AND` / `OR` logic based on query intent
5. Applies the filter directly to the WMS layer on the map — no page reload

---

## 🏗️ Architecture

```
Browser (HTML + OpenLayers)
        ↓  natural language query + layer name
FastAPI Backend (Python)
        ↓  1. fetch layer schema (attribute names + values)
        ↓  2. send schema + query to LLM (Groq / Llama 3.3 70B)
        ↓  3. LLM identifies relevant attributes and generates CQL filter
        ↓  4. return CQL filter string to frontend
GeoServer (WMS)
        ↓  WMS GetMap request with CQL_FILTER param applied
OpenLayers renders filtered layer on map
```

---

## ⚙️ Prerequisites

### GeoServer
- GeoServer running locally or on a remote server
- Layers published as WMS with attributes accessible
- WMS endpoint available (e.g. `http://localhost:8080/geoserver/wms`)

### Python
- Python 3.10+
- pip

### Groq API Key
- Free at [console.groq.com](https://console.groq.com)

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/SadhakAkshay/natural_language_cql_filter.git
cd dynamic_cql_filter
```

### 2. Backend setup

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GEOSERVER_URL=http://localhost:8080/geoserver
GEOSERVER_WORKSPACE=your_workspace
```

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

API live at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`


---

## 📡 API Reference

### `POST /api/get-columns`

Returns attribute names and their unique values for a given layer — used as the knowledge base for the LLM.

**Request:**
```json
{
  "layer_name": "india_districts"
}
```

**Response:**
```json
{
  "layer": "india_districts",
  "total_fields": 6,
  "attributes": [
    {
      "field": "state_name",
      "type": "string",
    },
    {
      "field": "population",
      "type": "int",
    }
  ]
}
```

---

### `POST /api/generate-sql`

Converts a natural language query into a CQL filter string ready to be applied to the WMS layer.

**Request:**
```json
{
  "layer_name": "india_districts",
  "query": "show me all districts in Maharashtra with population greater than 500000"
}
```

**Response:**
```json
{
  "layer": "india_districts",
  "query": "show me all districts in Maharashtra with population greater than 500000",
  "cql_filter": "state_name = 'Maharashtra' AND population > 500000",
  "logic_used": "AND"
}
```

The `cql_filter` is directly passed to the WMS `CQL_FILTER` parameter in OpenLayers.

---

## 🧠 How the NL → CQL Pipeline Works

```
1. SCHEMA DISCOVERY
   Fetch layer attributes + unique values from GeoServer
   Smart sampling for high-cardinality fields:
     → first 10 + middle 5 + last 5 unique values
   This forms the knowledge base passed to the LLM

2. LLM ATTRIBUTE IDENTIFICATION
   Llama 3.3 70B receives:
     → layer name
     → schema knowledge base (fields + sample values)
     → user's natural language query
   LLM identifies:
     → which fields are relevant
     → which values match (exact or contextual)
     → whether conditions should be AND or OR

3. CQL FILTER GENERATION
   LLM outputs a valid CQL filter string e.g.:
     → "state_name = 'Maharashtra' AND population > 500000"
     → "road_type = 'NH' OR road_type = 'SH'"
   temperature=0.1 for deterministic, low-hallucination output

4. WMS LAYER FILTERING
   Frontend receives the CQL filter string
   Applies it to the OpenLayers WMS source:
     params: { 'CQL_FILTER': cqlFilter }
   GeoServer re-renders only matching features
```

---

## 🔀 Dynamic AND / OR Handling

The LLM understands query intent to decide the correct logic operator:

| User Query | Logic | CQL Filter Generated |
|---|---|---|
| "Show Maharashtra and Gujarat" | `OR` | `state_name = 'Maharashtra' OR state_name = 'Gujarat'` |
| "Districts in Maharashtra with high population" | `AND` | `state_name = 'Maharashtra' AND population > 500000` |
| "National highways or expressways" | `OR` | `road_type = 'NH' OR road_type = 'EXP'` |
| "Show roads in Maharashtra that are national highways" | `AND` | `state_name = 'Maharashtra' AND road_type = 'NH'` |

The LLM reasons about whether the user is **narrowing** results (AND) or **expanding** results (OR) based on context — not just keywords.

---

## 🖥️ Frontend Features

- **Layer selector** — dynamically populated from GeoServer WMS GetCapabilities
- **Attribute panel** — field names, types, and sample values shown on layer select
- **Natural language input** — type your query and click "Show on Map"
- **Live WMS filtering** — CQL filter applied to WMS layer without reloading the page
- **Feature info on click** — click map features to inspect attribute values

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Map rendering | [OpenLayers 10](https://openlayers.org/) |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) |
| LLM | [Llama 3.3 70B Versatile](https://groq.com/) via Groq |
| GIS Server | [GeoServer](https://geoserver.org/) |
| Spatial protocol | OGC WMS 1.1.1 / 1.3.0 |
| Filter language | [CQL (Common Query Language)](https://docs.geoserver.org/stable/en/user/tutorials/cql/cql_tutorial.html) |

---

## 📊 CQL vs OGC XML Filter

This project uses **CQL** (GeoServer's native filter language) instead of OGC XML filters used in WFS:

| | CQL | OGC XML Filter |
|---|---|---|
| Syntax | `state = 'MH' AND pop > 500000` | Verbose XML |
| Used in | WMS `CQL_FILTER` param | WFS `FILTER` param |
| Server | GeoServer | QGIS Server / any WFS |
| LLM friendliness | ✅ Simple, readable | ⚠️ Verbose XML |

---

## 🙌 Acknowledgements

- [GeoServer](https://geoserver.org/) for the open-source OGC-compliant map server
- [Groq](https://groq.com/) for blazing fast Llama inference
- [OpenLayers](https://openlayers.org/) for the mapping library
- [OGC](https://www.ogc.org/) for WMS and CQL standards
