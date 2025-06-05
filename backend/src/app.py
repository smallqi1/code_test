from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "supports_credentials": True}})

# 使用start_server.py来启动所有服务
# 这个文件仅作为服务容器

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 