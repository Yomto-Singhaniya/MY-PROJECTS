import io
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "image_classifier.keras"
CLASS_NAMES_PATH = BASE_DIR / "class_names.json"
FRONTEND_DIR = BASE_DIR.parent / "frontend"
IMAGE_SIZE = (160, 160)
MAX_FILE_SIZE = 10 * 1024 * 1024

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("skyscan")

model: Any = None
class_names: list[str] = []
model_message = "Model files have not been added yet."


def load_model_files() -> None:
    global model, class_names, model_message

    missing = [
        path.name for path in (MODEL_PATH, CLASS_NAMES_PATH) if not path.is_file()
    ]
    if missing:
        model = None
        class_names = []
        model_message = f"Missing required model file(s): {', '.join(missing)}."
        logger.warning(model_message)
        return

    try:
        with CLASS_NAMES_PATH.open("r", encoding="utf-8") as file:
            names = json.load(file)
        if not isinstance(names, list) or not names or not all(
            isinstance(name, str) and name.strip() for name in names
        ):
            raise ValueError("class_names.json must contain a non-empty array of names")

        from tensorflow.keras.models import load_model as keras_load_model

        loaded_model = keras_load_model(MODEL_PATH)
        model = loaded_model
        class_names = names
        model_message = "Model loaded successfully."
        logger.info("Loaded model with %d classes", len(class_names))
    except Exception as exc:
        model = None
        class_names = []
        model_message = f"Could not load model files: {exc}"
        logger.exception(model_message)


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_model_files()
    yield


app = FastAPI(title="SkyScan API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "%s %s completed in %.1f ms",
            request.method,
            request.url.path,
            elapsed_ms,
        )


def preprocess_image(image: Image.Image) -> np.ndarray:
    # Must match training. Check whether training used
    # mobilenet_v2.preprocess_input ([-1, 1]) or Rescaling(1/255) inside the model.
    rgb_image = image.convert("RGB").resize(IMAGE_SIZE)
    pixels = np.asarray(rgb_image, dtype=np.float32)
    return np.expand_dims((pixels / 127.5) - 1.0, axis=0)


@app.get("/")
async def welcome():
    return {"message": "Welcome to SkyScan — Multi-Class Image Recognition."}


@app.get("/app", include_in_schema=False)
async def frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "classes": len(class_names),
        "message": model_message,
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if file.content_type and not file.content_type.lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    contents = await file.read(MAX_FILE_SIZE + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Image must be 10 MB or smaller.")
    try:
        with Image.open(io.BytesIO(contents)) as image:
            image.load()
            input_tensor = preprocess_image(image)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not read the uploaded image. Please try a valid image file.",
        ) from exc

    if model is None:
        raise HTTPException(
            status_code=503,
            detail=f"Classifier is unavailable. {model_message}",
        )

    try:
        predictions = np.asarray(model.predict(input_tensor, verbose=0)).reshape(-1)
        if predictions.size != len(class_names):
            raise ValueError(
                f"Model returned {predictions.size} scores for "
                f"{len(class_names)} class names."
            )
        if not np.all(np.isfinite(predictions)):
            raise ValueError("Model returned invalid prediction scores.")

        top_indices = np.argsort(predictions)[::-1][: min(3, len(class_names))]
        top3 = [
            {
                "class": class_names[int(index)],
                "confidence": float(predictions[index]),
            }
            for index in top_indices
        ]
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(
            status_code=500, detail=f"Prediction failed: {exc}"
        ) from exc

    return {
        "predicted_class": top3[0]["class"],
        "confidence": top3[0]["confidence"],
        "top3": top3,
    }


app.mount(
    "/vendor",
    StaticFiles(directory=FRONTEND_DIR / "vendor"),
    name="frontend-vendor",
)
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="frontend-static",
)
