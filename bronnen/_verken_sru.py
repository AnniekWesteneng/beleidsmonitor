"""Verkenningsscript: haal de RUWE SRU-respons op en print 'm.

Doel: zien hoe de API echt antwoordt VOORDAT we parsing schrijven.
Draaien: python bronnen/_verken_sru.py
"""
import requests

SRU_ENDPOINT = "https://repository.overheid.nl/sru"

# We proberen een eenvoudige query: collectie officiele publicaties,
# vrije-tekst 'bedrijventerrein'. De exacte veldnamen verifieren we via de output.
params = {
    "operation": "searchRetrieve",
    "version": "2.0",
    "maximumRecords": "3",
    "query": '(c.product-area==officielepublicaties) and (cql.textAndIndexes="bedrijventerrein")',
}

print(f"GET {SRU_ENDPOINT}")
print(f"query = {params['query']}\n")

resp = requests.get(SRU_ENDPOINT, params=params, timeout=30)
print("HTTP status:", resp.status_code)
print("Content-Type:", resp.headers.get("Content-Type"))
print("URL:", resp.url)
print("\n===== EERSTE 4000 TEKENS VAN DE RESPONS =====\n")
print(resp.text[:4000])
