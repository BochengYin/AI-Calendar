from flask import Flask, jsonify
import os
import logging
import socket

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/', methods=['GET'])
def root():
    """Root endpoint for diagnostics."""
    # Get system info
    hostname = socket.gethostname()
    port = os.environ.get('PORT', '10000')
    
    # Log details
    logger.info(f"Root endpoint called on {hostname} using port {port}")
    logger.info(f"Environment variables: PORT={port}")
    
    return jsonify({
        'status': 'ok',
        'message': 'Simple diagnostic Flask app is running',
        'hostname': hostname,
        'port': port,
        'environ': {k: v for k, v in os.environ.items() if not k.startswith('OPENAI') and not 'KEY' in k}
    })

@app.route('/health', methods=['GET'])
def health():
    """Simple health check."""
    return jsonify({
        'status': 'ok',
        'message': 'Health check endpoint is working'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Starting simple diagnostic app on port {port}")
    app.run(host='0.0.0.0', port=port) 