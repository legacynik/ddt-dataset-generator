# Azure Document Intelligence Analysis

Scripts per analizzare e confrontare i diversi modelli OCR di Azure.

## Scripts

### test_layout_vs_read.py

Confronta i tre approcci OCR:
1. **Azure prebuilt-read** (attuale) - Solo testo raw
2. **Azure prebuilt-layout + markdown** - Testo strutturato con tabelle HTML
3. **Datalab Marker** - Markdown con figure e descrizioni

**Uso:**
```bash
cd /Users/franzoai/ddt-dataset-generator/backend

# Test singolo documento
SSL_CERT_FILE=/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/certifi/cacert.pem \
python3 tests/azure_analysis/test_layout_vs_read.py --file doc01128620251217151633_008.pdf

# Confronto multiplo (default 5 documenti)
SSL_CERT_FILE=/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/certifi/cacert.pem \
python3 tests/azure_analysis/test_layout_vs_read.py --compare 10
```

## Risultati Analisi

### Confronto Output (5 documenti)

| Documento | Azure Read | Azure Layout | Datalab |
|-----------|------------|--------------|---------|
| doc...008.pdf | 1,078 | 2,569 (+2.4x) | 2,735 (+2.5x) |
| doc...003.pdf | 2,318 | 5,787 (+2.5x) | 23,989 (+10.3x) |
| testScansione2.pdf | 2,318 | 5,789 (+2.5x) | 25,786 (+11.1x) |
| testScansione5.pdf | 1,663 | 2,905 (+1.7x) | 3,151 (+1.9x) |
| doc...015.pdf | 2,343 | 5,437 (+2.3x) | 15,096 (+6.4x) |

### Elementi Strutturali Estratti

| Modello | Tabelle | Paragrafi | Figure | Checkbox |
|---------|---------|-----------|--------|----------|
| prebuilt-read | ❌ | ❌ | ❌ | ❌ |
| prebuilt-layout | ✅ HTML | ✅ | ✅ `<figure>` | ✅ Unicode ☐☒ |
| Datalab | ✅ Markdown | ✅ | ✅ con caption | ✅ |

## Costi Azure

| Modello | Prezzo/1000 pagine | Uso consigliato |
|---------|-------------------|-----------------|
| prebuilt-read | $1.50 | Solo testo, no struttura |
| prebuilt-layout | $10.00 | Documenti strutturati (DDT) |

## Raccomandazione

Per i DDT (Documenti Di Trasporto), usare `prebuilt-layout` con `outputContentFormat=markdown`:
- Estrae tabelle in HTML (righe ordine, descrizioni merce)
- Riconosce checkbox (mittente/destinatario/vettore)
- Identifica figure (loghi, timbri)
- Output 2-2.5x più ricco di prebuilt-read
