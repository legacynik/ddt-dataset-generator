"""Schemas and models for DDT extraction.

This module contains:
- DDT extraction JSON schema (used by Datalab API)
- Pydantic models for extraction results
- Type definitions for extractor outputs
"""

import json
from typing import Optional
from pydantic import BaseModel, Field
from datetime import date


# DDT Extraction Schema for Datalab API
# This schema is sent to Datalab to guide the structured extraction
DDT_EXTRACTION_SCHEMA = {
    "type": "object",
    "title": "DDTExtractionSchema",
    "description": "Schema for DDT structured data extraction",
    "properties": {
        "mittente": {
            "type": "string",
            "description": "Estrai SOLO la Ragione Sociale (Nome Azienda) che emette il documento. Solitamente è il logo principale in alto. Regola: Non includere l'indirizzo, solo il nome (es. 'Barilla S.p.A.'). Ignora il Vettore."
        },
        "destinatario": {
            "type": "string",
            "description": "Estrai SOLO la Ragione Sociale (Nome Azienda) del cliente finale che riceve la merce. Regola: Non includere l'indirizzo, solo il nome (es. 'Mario Rossi SRL'). Se ci sono più nomi, dai priorità a quello nell'area 'Destinazione Merce'."
        },
        "indirizzo_destinazione_completo": {
            "type": "string",
            "description": "Estrai SOLO l'indirizzo fisico di consegna (Via, Civico, CAP, Città, Provincia). Logica: Se l'indirizzo di 'Destinazione Merce' è diverso dalla Sede Legale/Fatturazione, estrai tassativamente quello di Destinazione/Consegna. Non includere il nome dell'azienda qui."
        },
        "data_documento": {
            "type": "string",
            "description": "La data di emissione scritta sul documento (Data bolla/DDT). Cerca 'Data Documento', 'Data DDT'. Formato: Restituisci sempre in formato standard YYYY-MM-DD."
        },
        "data_trasporto": {
            "type": "string",
            "description": "La data specifica di inizio trasporto o data ritiro merce. Cerca 'Data inizio trasporto', 'Data consegna', 'Data partenza'. Logica: Questa data è spesso diversa dalla data del documento. Se non è presente esplicitamente, restituisci null."
        },
        "data_consegna_effettiva": {
            "type": "string",
            "description": "La data di consegna effettiva scritta a mano o timbrata sul documento. Cerca 'Data consegna', 'Consegnato il', timbri con data. Spesso è diversa dalla data trasporto. Se non presente, restituisci null."
        },
        "numero_documento": {
            "type": "string",
            "description": "Il numero identificativo univoco della Bolla o DDT (es. 'N. 1234/A'). Cerca 'Numero Bolla', 'Nr. DDT', 'Doc n.'."
        },
        "numero_ordine": {
            "type": "string",
            "description": "Estrai il codice indicato come 'Rif. Ordine', 'Vs. Ordine', 'Ordine Cliente'. Se non presente, restituisci null."
        },
        "codice_cliente": {
            "type": "string",
            "description": "Estrai il codice indicato come 'Codice Cliente', 'Cod. Cli.' o simili. Se non presente, restituisci null."
        },
        "targa_automezzo": {
            "type": "string",
            "description": "La targa del veicolo di trasporto. Cerca 'Targa', 'Automezzo', 'Mezzo'. Formato tipico: AA123BB. Se non presente, restituisci null."
        }
    },
    "required": [
        "mittente",
        "destinatario",
        "indirizzo_destinazione_completo",
        "data_documento",
        "numero_documento"
    ]
}

# JSON string version for API submission
DDT_EXTRACTION_SCHEMA_JSON = json.dumps(DDT_EXTRACTION_SCHEMA)


class DDTOutput(BaseModel):
    """Pydantic model for DDT extracted data.

    This model represents the structured output after extraction,
    matching the schema defined above.
    """

    mittente: str = Field(..., description="Ragione sociale mittente")
    destinatario: str = Field(..., description="Ragione sociale destinatario")
    indirizzo_destinazione_completo: str = Field(..., description="Indirizzo completo consegna")
    data_documento: str = Field(..., description="Data documento in formato YYYY-MM-DD")
    numero_documento: str = Field(..., description="Numero DDT/Bolla")

    # Optional fields
    data_trasporto: Optional[str] = Field(None, description="Data inizio trasporto (YYYY-MM-DD)")
    data_consegna_effettiva: Optional[str] = Field(None, description="Data consegna effettiva (YYYY-MM-DD)")
    numero_ordine: Optional[str] = Field(None, description="Numero ordine cliente")
    codice_cliente: Optional[str] = Field(None, description="Codice cliente")
    targa_automezzo: Optional[str] = Field(None, description="Targa veicolo di trasporto")

    class Config:
        json_schema_extra = {
            "example": {
                "mittente": "LAVAZZA S.p.A.",
                "destinatario": "CONAD SOC. COOP.",
                "indirizzo_destinazione_completo": "Via Roma 123, 20100 Milano (MI)",
                "data_documento": "2025-01-15",
                "data_trasporto": "2025-01-16",
                "data_consegna_effettiva": "2025-01-16",
                "numero_documento": "DDT-2025-001",
                "numero_ordine": "ORD-5678",
                "codice_cliente": "CLI-1234",
                "targa_automezzo": "AB123CD"
            }
        }


class DatalabResult(BaseModel):
    """Result from Datalab extraction.

    Contains both the raw OCR text (markdown format) and the
    structured JSON extraction.
    """

    raw_ocr: str = Field(..., description="Raw OCR text in markdown format")
    extracted_json: dict = Field(..., description="Structured DDT data as JSON")
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    success: bool = Field(default=True, description="Whether extraction was successful")
    error_message: Optional[str] = Field(None, description="Error message if extraction failed")

    class Config:
        json_schema_extra = {
            "example": {
                "raw_ocr": "# DDT N. 123\n\nMittente: LAVAZZA...",
                "extracted_json": {
                    "mittente": "LAVAZZA S.p.A.",
                    "destinatario": "CONAD SOC. COOP.",
                    "indirizzo_destinazione_completo": "Via Roma 123, 20100 Milano (MI)",
                    "data_documento": "2025-01-15",
                    "numero_documento": "DDT-2025-001"
                },
                "processing_time_ms": 8500,
                "success": True,
                "error_message": None
            }
        }


class AzureOCRResult(BaseModel):
    """Result from Azure Document Intelligence OCR.

    Contains the raw extracted text from the PDF.
    """

    raw_text: str = Field(..., description="Raw OCR text extracted")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    success: bool = Field(default=True, description="Whether OCR was successful")
    error_message: Optional[str] = Field(None, description="Error message if OCR failed")

    class Config:
        json_schema_extra = {
            "example": {
                "raw_text": "DDT N. 123\nMittente: LAVAZZA S.p.A.\n...",
                "processing_time_ms": 3200,
                "success": True,
                "error_message": None
            }
        }


class GeminiResult(BaseModel):
    """Result from Gemini extraction.

    Contains the structured extraction from OCR text.
    """

    extracted_json: dict = Field(..., description="Structured DDT data as JSON")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    success: bool = Field(default=True, description="Whether extraction was successful")
    error_message: Optional[str] = Field(None, description="Error message if extraction failed")

    class Config:
        json_schema_extra = {
            "example": {
                "extracted_json": {
                    "mittente": "LAVAZZA S.p.A.",
                    "destinatario": "CONAD SOC. COOP.",
                    "indirizzo_destinazione_completo": "Via Roma 123, 20100 Milano (MI)",
                    "data_documento": "2025-01-15",
                    "numero_documento": "DDT-2025-001"
                },
                "processing_time_ms": 2100,
                "success": True,
                "error_message": None
            }
        }
