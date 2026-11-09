# SkyScan — Multi-Class Image Recognition

SkyScan is a browser-based image classifier backed by a FastAPI service and a
TensorFlow/Keras model. The responsive interface includes an animated Three.js
background, image preview, drag-and-drop upload, top-three confidence display,
and an editable API URL for local or remote servers.

## Project layout

```text
plant-classifier-app/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── test_api.py
│   ├── image_classifier.keras   # add your trained model
│   └── class_names.json         # add ordered class names
├── frontend/
│   ├── index.html
│   └── vendor/
│       └── three.min.js         # Three.js r149, bundled locally
├── run.bat
├── Dockerfile
└── README.md
```

The trained model and class names are ignored by Git. Put
`image_classifier.keras` and `class_names.json` directly in `backend/`.
`class_names.json` must be a JSON string array in the same output order as the
model, for example `["class_one", "class_two"]`.

The frontend loads the local classic UMD build of Three.js r149 from
`frontend/vendor/three.min.js`. It does not require a CDN or ES modules.
The bundled library is distributed under the MIT license; see
`frontend/vendor/THREE-LICENSE.txt`.

## Local setup

Python 3.10 or 3.11 is recommended for TensorFlow compatibility.

### Windows

From the project directory, create and populate the backend environment once:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

To start the app, go back to the project root and double-click `run.bat` (or
run it from Command Prompt). It activates the backend virtual environment,
starts Uvicorn, waits for the health endpoint, and opens
`http://127.0.0.1:8000/app` in your browser.

You can also run the server manually:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### macOS/Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://127.0.0.1:8000/app`. SkyScan saves the API Base URL in browser
local storage and checks the connection on page load and when the URL changes.
The backend can start without the model files; `/health` reports
`"model_loaded": false`, and `/predict` returns HTTP 503 with a clear reason.

## API

- `GET /` — SkyScan welcome message.
- `GET /app` — serves the browser interface.
- `GET /health` — returns service status, `model_loaded`, class count, and a
  message.
- `POST /predict` — accepts an image in multipart field `file`; returns the
  predicted class, confidence, and up to three ranked predictions.

Example:

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "ngrok-skip-browser-warning: true" \
  -F "file=@image.jpg"
```

Successful response:

```json
{
  "predicted_class": "example_class",
  "confidence": 0.93,
  "top3": [
    {"class": "example_class", "confidence": 0.93},
    {"class": "another_class", "confidence": 0.04},
    {"class": "third_class", "confidence": 0.02}
  ]
}
```

With the model installed, run `python test_api.py` from `backend/` to send a
generated sample image. For a real image, use
`python test_api.py --image path/to/image.jpg --url http://127.0.0.1:8000`.

## Kaggle/Colab and tunnels

1. Install the backend requirements and place both model files in `backend/`.
2. Start Uvicorn on `0.0.0.0:8000`.
3. Use the notebook's supported tunnel integration to expose port 8000 and
   copy its HTTPS URL.
4. Paste that URL in SkyScan's API Base URL field and check the connection.

Keep tunnel authentication tokens private. Some notebook environments provide
their own port forwarding and may not need ngrok.

## Docker

From the project root:

```bash
docker build -t skyscan .
docker run --rm -p 8000:8000 skyscan
```

The local model files must be present in the Docker build context for the
container to load a model.

## Troubleshooting

- **3D background not showing:** Confirm `frontend/vendor/three.min.js` exists
  and that the browser can load `/vendor/three.min.js` (or the relative
  `vendor/three.min.js` URL when opening the HTML directly). The local script
  is Three.js r149 from
  <https://unpkg.com/three@0.149.0/build/three.min.js>.
- **WebGL disabled or unavailable:** Enable hardware acceleration/WebGL in the
  browser or try a supported browser. SkyScan catches renderer errors and uses
  a CSS gradient background while keeping the interface functional.
- **Model missing:** Confirm `backend/image_classifier.keras` and
  `backend/class_names.json` are present. Check `GET /health` for the detailed
  message.
- **Incorrect predictions:** Confirm training preprocessing matches
  `preprocess_image()` in `backend/main.py`. It currently scales pixels to
  `[-1, 1]`; if the model expects `Rescaling(1/255)` inside the model, update
  the preprocessing to match the training pipeline.
- **Port in use:** Stop the other process using port 8000 or choose another
  Uvicorn port and update SkyScan's API Base URL.
- **TensorFlow installation/import:** Use a supported Python version and
  TensorFlow build. If native Windows blocks a TensorFlow DLL, use WSL, Linux,
  or Docker.
- **CORS or remote API:** CORS is enabled by the backend. A reverse proxy or
  hosting provider must also forward `OPTIONS` and CORS response headers.

## Future improvements

- Add batch upload and prediction history.
- Store preprocessing metadata alongside the model.
- Restrict CORS and add authentication/rate limiting for public deployments.
- Add automated tests using a representative model and image fixtures.
