"""Entry point for TeraCast API."""
import os
from api import app


def main() -> None:
    """Run the Flask development server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    
    print(f"🚀 Starting TeraCast API server...")
    print(f"📍 Running on http://{host}:{port}")
    print(f"🔧 Debug mode: {'ON' if debug else 'OFF'}")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
