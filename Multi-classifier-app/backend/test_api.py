import argparse
import json
import mimetypes
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a sample image to /predict.")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--image",
        type=Path,
        help="Image file to upload. A temporary sample PNG is used if omitted.",
    )
    args = parser.parse_args()

    boundary = uuid.uuid4().hex
    if args.image:
        image_bytes = args.image.read_bytes()
        filename = args.image.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    else:
        from io import BytesIO

        buffer = BytesIO()
        Image.new("RGB", (160, 160), color=(72, 140, 80)).save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        filename = "sample.png"
        content_type = "image/png"

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + image_bytes + f"\r\n--{boundary}--\r\n".encode()

    request = Request(
        f"{args.url.rstrip('/')}/predict",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "ngrok-skip-browser-warning": "true",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            print(json.dumps(json.loads(response.read()), indent=2))
    except HTTPError as exc:
        print(f"Server returned HTTP {exc.code}: {exc.read().decode(errors='replace')}")
        raise SystemExit(1) from exc
    except URLError as exc:
        print(f"Could not reach API at {args.url}: {exc.reason}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
