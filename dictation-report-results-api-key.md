# Dictation Report Results API Key Usage

This endpoint lets you generate the patient-friendly PDF from a dictation report using an API key.

## Endpoint

`POST /relisten/dictation/process/report-results`

## Authentication

Send your API key in the `X-API-Key` header.

```http
X-API-Key: rrk_yourPublicId_yourSecret
```

Do not send `Authorization: Bearer ...` together with `X-API-Key` in the same request.

## Request body

The request body must be JSON with:

- `dictationReport`: the source report text you want to transform into the final PDF

### Simplest example

```json
{
  "dictationReport": "Paciente con dolor abdominal de 48 horas. Se solicita analitica y ecografia. Se explican signos de alarma."
}
```

## cURL example

```bash
curl --request POST "https://api.recog.es/relisten/dictation/process/report-results" \
  --header "Content-Type: application/json" \
  --header "X-API-Key: rrk_yourPublicId_yourSecret" \
  --data '{
    "dictationReport": "Paciente con dolor abdominal de 48 horas. Se solicita analitica y ecografia. Se explican signos de alarma."
  }' \
  --output report-results.pdf
```

## Python example

```python
import requests

response = requests.post(
    "https://api.recog.es/relisten/dictation/process/report-results",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": "rrk_yourPublicId_yourSecret",
    },
    json={
        "dictationReport": (
            "Paciente con dolor abdominal de 48 horas. "
            "Se solicita analitica y ecografia. Se explican signos de alarma."
        ),
    },
    timeout=60,
)

response.raise_for_status()

with open("report-results.pdf", "wb") as file:
    file.write(response.content)
```

## JavaScript example

```javascript
const response = await fetch(
  "https://api.recog.es/relisten/dictation/process/report-results",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": "rrk_yourPublicId_yourSecret",
    },
    body: JSON.stringify({
      dictationReport:
        "Paciente con dolor abdominal de 48 horas. Se solicita analitica y ecografia. Se explican signos de alarma.",
    }),
  },
);

if (!response.ok) {
  throw new Error(`Request failed: ${response.status}`);
}

const pdfBuffer = await response.arrayBuffer();
```

## Response

If the request is valid, the API returns a PDF file.

## Common errors

- `401 Unauthorized`: the API key is missing or invalid
- `403 Forbidden`: the key is expired, revoked, over its limits, or not allowed for this pipeline
- `429 Too Many Requests`: the key exceeded its requests-per-second limit
- `503 Service Unavailable`: rate limiting is temporarily unavailable for API key requests
