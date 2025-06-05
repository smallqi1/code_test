#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户认证API服务
提供用户注册、登录、验证、密码重置等功能
"""

import os
import sys
import logging
from pathlib import Path
import mysql.connector
from mysql.connector import Error
import hashlib
import uuid
import time
import json
from datetime import datetime, timedelta
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import random
import string
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 设置项目根目录
project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
sys.path.append(project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_root, 'logs', 'user_auth_api.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger('user_auth_api')

# 数据库配置
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME', 'air_quality_monitoring'),
    'port': int(os.environ.get('DB_PORT', '3306'))
}

# Validate that password is loaded
if not DB_CONFIG['password']:
    raise ValueError("DB_PASSWORD environment variable is required but not set")

# JWT配置
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required but not set")

JWT_EXPIRATION = 24 * 3600  # 24小时过期

# 创建Flask应用
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:3001"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Cache-Control", "pragma"]
    }
}, supports_credentials=True)

# 添加响应头以允许CORS请求
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3001'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Cache-Control, pragma'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '86400'  # 24小时
    return response

# 定义可用的密保问题列表
SECURITY_QUESTIONS = [
    "您的出生地是哪里？",
    "您的母亲的姓名是什么？",
    "您的父亲的姓名是什么？",
    "您的初中班主任姓什么？",
    "您的第一只宠物的名字是什么？",
    "您的第一辆车的品牌是什么？",
    "您最喜欢的电影是什么？"
]

# 定义用户角色常量
USER_ROLE_SUPER_ADMIN = 'super_admin'  # 超级管理者
USER_ROLE_ADMIN = 'admin'              # 管理员
USER_ROLE_USER = 'user'                # 普通用户

# 定义最大管理员数量
MAX_ADMIN_COUNT = 5

def connect_to_db():
    """连接到数据库"""
    try:
        logger.debug("正在连接到数据库...")
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            logger.debug("数据库连接成功")
            return conn
        logger.error("数据库连接失败：未能建立连接")
        return None
    except Error as e:
        logger.error(f"数据库连接错误: {e}")
        return None

def init_database():
    """初始化数据库，创建用户表"""
    logger.info("正在初始化用户数据库...")
    conn = connect_to_db()
    if not conn:
        logger.error("初始化数据库失败：无法连接到数据库")
        return False
    
    try:
        cursor = conn.cursor()
        
        # 创建users表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(128) NOT NULL,
            salt VARCHAR(32) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            role VARCHAR(20) DEFAULT 'user',
            status VARCHAR(20) DEFAULT 'active',
            avatar VARCHAR(255) DEFAULT NULL,
            reset_token VARCHAR(64) DEFAULT NULL,
            reset_token_expires TIMESTAMP NULL,
            INDEX idx_username (username),
            INDEX idx_email (email),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        # 检查是否需要添加密保问题字段
        cursor.execute("SHOW COLUMNS FROM users LIKE 'security_questions'")
        if not cursor.fetchone():
            # 添加存储密保问题和答案的字段
            cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN security_questions JSON DEFAULT NULL,
            ADD COLUMN has_security_questions BOOLEAN DEFAULT FALSE;
            """)
            logger.info("添加了密保问题相关字段")
            
        # 设置用户名为12306的用户为超级管理者
        cursor.execute("""
        UPDATE users SET role = %s WHERE username = %s
        """, (USER_ROLE_SUPER_ADMIN, '12306'))
        affected_rows = cursor.rowcount
        if affected_rows > 0:
            logger.info(f"已将用户 12306 设置为超级管理者")
        
        logger.info("用户表创建或已存在")
        conn.commit()
        return True
    except Error as e:
        logger.error(f"初始化数据库错误: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def hash_password(password, salt=None):
    """使用SHA256对密码进行哈希"""
    if salt is None:
        salt = uuid.uuid4().hex
    
    # 组合密码和盐值进行哈希
    hash_obj = hashlib.sha256()
    hash_obj.update((password + salt).encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    
    return password_hash, salt

def validate_password(password):
    """验证密码强度"""
    # 密码长度至少为8个字符
    if len(password) < 8:
        return False, "密码长度必须至少为8个字符"
    
    # 密码必须包含字母和数字
    if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
        return False, "密码必须包含字母和数字"
    
    return True, ""

def validate_email(email):
    """验证邮箱格式"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, email):
        return True
    return False

def create_jwt_token(user_id, username, role):
    """创建JWT令牌"""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': int(time.time()) + JWT_EXPIRATION
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
    return token

def verify_jwt_token(token):
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册API"""
    data = request.get_json()
    
    # 验证必填字段
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'message': f'缺少必填字段: {field}'}), 400
    
    username = data['username']
    email = data['email']
    password = data['password']
    
    # 验证用户名长度
    if len(username) < 3 or len(username) > 20:
        return jsonify({'success': False, 'message': '用户名长度必须在3到20个字符之间'}), 400
    
    # 验证邮箱格式
    if not validate_email(email):
        return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400
    
    # 验证密码强度
    valid_password, password_message = validate_password(password)
    if not valid_password:
        return jsonify({'success': False, 'message': password_message}), 400
    
    # 哈希密码
    password_hash, salt = hash_password(password)
    
    # 连接数据库
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor()
        
        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': '用户名已存在'}), 400
        
        # 检查邮箱是否已存在
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': '邮箱已被注册'}), 400
        
        # 插入新用户
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, salt, role)
        VALUES (%s, %s, %s, %s, %s)
        """, (username, email, password_hash, salt, 'user'))
        
        conn.commit()
        
        # 获取新用户ID
        user_id = cursor.lastrowid
        
        # 创建JWT令牌
        token = create_jwt_token(user_id, username, 'user')
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'token': token,
            'user': {
                'id': user_id,
                'username': username,
                'email': email,
                'role': 'user'
            }
        }), 201
        
    except Error as e:
        logger.error(f"注册用户错误: {e}")
        return jsonify({'success': False, 'message': f'注册失败: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录API"""
    data = request.get_json()
    
    # 验证必填字段
    required_fields = ['username', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'message': f'缺少必填字段: {field}'}), 400
    
    username = data['username']
    password = data['password']
    
    # 连接数据库
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor()
        
        # 查询用户信息（支持用户名或邮箱登录）
        cursor.execute("""
        SELECT id, username, email, password_hash, salt, role, status 
        FROM users 
        WHERE username = %s OR email = %s
        """, (username, username))
        
        user = cursor.fetchone()
        
        # 用户不存在
        if not user:
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
        
        user_id, db_username, email, password_hash, salt, role, status = user
        
        # 检查用户状态
        if status == 'banned':
            return jsonify({'success': False, 'message': '账号已被封禁，请联系管理员'}), 403
        
        # 检查密码
        input_password_hash, _ = hash_password(password, salt)
        
        if input_password_hash != password_hash:
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
        
        # 更新最后登录时间
        cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
        conn.commit()
        
        # 创建JWT令牌
        token = create_jwt_token(user_id, db_username, role)
        
        # 判断是否为超级管理者
        is_super_admin = (role == USER_ROLE_SUPER_ADMIN)
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user_id,
                'username': db_username,
                'email': email,
                'role': role,
                'isSuperAdmin': is_super_admin
            }
        })
    except Error as e:
        logger.error(f"登录错误: {e}")
        return jsonify({'success': False, 'message': f'登录失败: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/auth/validate', methods=['GET'])
def validate_token():
    # 获取请求头中的令牌
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'message': '未授权：缺少有效的认证令牌'}), 401
    
    token = auth_header.split(' ')[1]
    payload = verify_jwt_token(token)
    
    if not payload:
        return jsonify({'success': False, 'message': '令牌无效或已过期'}), 401
    
    # 从数据库获取最新的用户信息
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
        SELECT id, username, email, role, status, avatar 
        FROM users 
        WHERE id = %s
        """, (payload['user_id'],))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        if user['status'] != 'active':
            return jsonify({'success': False, 'message': '账户已被封禁'}), 403
            
        is_user_super_admin = user['role'] == USER_ROLE_SUPER_ADMIN
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'isSuperAdmin': is_user_super_admin,
                'avatar': user['avatar']
            }
        })
    except Error as e:
        logger.error(f"验证令牌错误: {e}")
        return jsonify({'success': False, 'message': f'数据库错误: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/auth/change-password', methods=['POST'])
def change_password():
    """修改密码API"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'message': '无效的认证令牌格式'}), 401
    
    token = auth_header.split(' ')[1]
    
    try:
        # 验证令牌
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        
        # 获取请求数据
        data = request.get_json()
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        # 验证新密码强度
        valid_password, password_message = validate_password(new_password)
        if not valid_password:
            return jsonify({'success': False, 'message': password_message}), 400
        
        # 连接数据库
        conn = connect_to_db()
        if not conn:
            return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 验证当前密码
            cursor.execute("SELECT password_hash, salt FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
            
            # 使用相同的盐值计算当前密码的哈希值
            current_password_hash = hashlib.sha256((current_password + user['salt']).encode()).hexdigest()
            
            # 验证密码
            if current_password_hash != user['password_hash']:
                return jsonify({'success': False, 'message': '当前密码不正确'}), 400
            
            # 使用hash_password函数生成新的盐值和密码哈希
            new_password_hash, new_salt = hash_password(new_password)
            
            # 更新密码 - 确保所有参数都被使用
            cursor.execute(
                "UPDATE users SET password_hash = %s, salt = %s WHERE id = %s",
                (new_password_hash, new_salt, user_id)
            )
            
            # 确保提交更改
            conn.commit()
            
            logger.info(f"用户ID {user_id} 密码修改成功")
            return jsonify({'success': True, 'message': '密码修改成功'})
        except Error as e:
            logger.error(f"修改密码错误: {e}")
            return jsonify({'success': False, 'message': f'修改密码失败: {str(e)}'}), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'message': '认证令牌已过期'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'message': '无效的认证令牌'}), 401

@app.route('/api/auth/delete-account', methods=['DELETE'])
def delete_account():
    """注销账号API"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'message': '无效的认证令牌格式'}), 401
    
    token = auth_header.split(' ')[1]
    
    try:
        # 验证令牌
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        
        # 连接数据库
        conn = connect_to_db()
        if not conn:
            return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 检查用户是否存在
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
            
            # 删除用户
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            
            return jsonify({'success': True, 'message': '账号已成功注销'})
        except Error as e:
            logger.error(f"注销账号错误: {e}")
            return jsonify({'success': False, 'message': f'注销账号失败: {str(e)}'}), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'message': '认证令牌已过期'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'message': '无效的认证令牌'}), 401

@app.route('/api/auth/user', methods=['GET'])
def get_user_info():
    """获取用户信息API"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'message': '未提供认证令牌'}), 401
    
    token = auth_header.split(' ')[1]
    payload = verify_jwt_token(token)
    
    if not payload:
        return jsonify({'success': False, 'message': '无效或已过期的令牌'}), 401
    
    # 连接数据库获取用户信息
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 查询用户信息
        cursor.execute("""
        SELECT id, username, email, role, status, avatar, created_at, last_login
        FROM users 
        WHERE id = %s
        """, (payload['user_id'],))
        
        user = cursor.fetchone()
        
        # 验证用户存在
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        # 转换日期时间为ISO格式字符串
        if user['created_at']:
            user['created_at'] = user['created_at'].isoformat()
        if user['last_login']:
            user['last_login'] = user['last_login'].isoformat()
        
        return jsonify({
            'success': True,
            'user': user
        }), 200
        
    except Error as e:
        logger.error(f"获取用户信息错误: {e}")
        return jsonify({'success': False, 'message': f'获取用户信息失败: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/auth/security-questions', methods=['GET'])
def get_security_questions():
    """获取密保问题列表"""
    return jsonify({
        'success': True,
        'questions': SECURITY_QUESTIONS
    })

@app.route('/api/auth/security-questions/setup', methods=['POST'])
def setup_security_questions():
    """设置密保问题和答案"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'message': '无效的认证令牌格式'}), 401
    
    token = auth_header.split(' ')[1]
    
    try:
        # 验证令牌
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        
        # 获取请求数据
        data = request.get_json()
        
        if not data or 'questions' not in data:
            return jsonify({'success': False, 'message': '缺少密保问题数据'}), 400
        
        questions = data['questions']
        
        # 验证密保问题格式
        if not isinstance(questions, list) or len(questions) != 3:
            return jsonify({'success': False, 'message': '请选择3个密保问题及答案'}), 400
        
        for q in questions:
            if 'question' not in q or 'answer' not in q:
                return jsonify({'success': False, 'message': '密保问题格式不正确'}), 400
            if not q['question'] or not q['answer']:
                return jsonify({'success': False, 'message': '密保问题和答案不能为空'}), 400
            # 验证问题是否在预设列表中
            if q['question'] not in SECURITY_QUESTIONS:
                return jsonify({'success': False, 'message': '包含无效的密保问题'}), 400
        
        # 连接数据库
        conn = connect_to_db()
        if not conn:
            return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 保存密保问题
            security_questions_json = json.dumps(questions)
            cursor.execute(
                "UPDATE users SET security_questions = %s, has_security_questions = TRUE WHERE id = %s",
                (security_questions_json, user_id)
            )
            conn.commit()
            
            logger.info(f"用户ID {user_id} 设置了密保问题")
            return jsonify({'success': True, 'message': '密保问题设置成功'})
        except Error as e:
            logger.error(f"设置密保问题错误: {e}")
            return jsonify({'success': False, 'message': f'设置密保问题失败: {str(e)}'}), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'message': '认证令牌已过期'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'message': '无效的认证令牌'}), 401

@app.route('/api/auth/security-questions/user', methods=['GET'])
def get_user_security_questions():
    """获取用户当前的密保问题设置状态"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'message': '无效的认证令牌格式'}), 401
    
    token = auth_header.split(' ')[1]
    
    try:
        # 验证令牌
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        
        # 连接数据库
        conn = connect_to_db()
        if not conn:
            return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 查询用户的密保问题状态
            cursor.execute(
                "SELECT has_security_questions, security_questions FROM users WHERE id = %s", 
                (user_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
            
            result = {
                'success': True,
                'hasSecurityQuestions': user['has_security_questions']
            }
            
            # 如果用户已设置密保问题，返回问题（不含答案）
            if user['has_security_questions'] and user['security_questions']:
                questions = json.loads(user['security_questions'])
                # 只返回问题，不返回答案
                questions_only = [{'question': q['question']} for q in questions]
                result['questions'] = questions_only
            
            return jsonify(result)
        except Error as e:
            logger.error(f"获取用户密保问题状态错误: {e}")
            return jsonify({'success': False, 'message': f'获取密保问题状态失败: {str(e)}'}), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'message': '认证令牌已过期'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'message': '无效的认证令牌'}), 401

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password_init():
    """初始化忘记密码流程，获取用户的密保问题"""
    data = request.get_json()
    
    if not data or 'username' not in data:
        return jsonify({'success': False, 'message': '缺少用户名或邮箱'}), 400
    
    username = data['username']
    
    # 连接数据库
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 查询用户
        cursor.execute("""
        SELECT id, username, has_security_questions, security_questions 
        FROM users 
        WHERE username = %s OR email = %s
        """, (username, username))
        
        user = cursor.fetchone()
        
        # 验证用户存在
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        # 验证用户是否设置了密保问题
        if not user['has_security_questions'] or not user['security_questions']:
            return jsonify({
                'success': False, 
                'message': '未设置密保问题，无法重置密码。请联系管理员处理'
            }), 400
        
        # 提取用户的密保问题（不包含答案）
        security_questions = json.loads(user['security_questions'])
        questions_only = [{'id': idx, 'question': q['question']} for idx, q in enumerate(security_questions)]
        
        # 创建重置密码令牌
        reset_token = uuid.uuid4().hex
        expires = datetime.now() + timedelta(hours=1)  # 1小时有效期
        
        # 保存重置令牌
        cursor.execute(
            "UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE id = %s",
            (reset_token, expires, user['id'])
        )
        conn.commit()
        
        return jsonify({
            'success': True,
            'userId': user['id'],
            'username': user['username'],
            'questions': questions_only,
            'resetToken': reset_token
        })
    except Error as e:
        logger.error(f"忘记密码流程错误: {e}")
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/auth/verify-security-answers', methods=['POST'])
def verify_security_answers():
    """验证用户的密保问题答案"""
    data = request.get_json()
    
    if not data or 'userId' not in data or 'resetToken' not in data or 'answers' not in data:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    user_id = data['userId']
    reset_token = data['resetToken']
    answers = data['answers']
    
    # 验证答案格式
    if not isinstance(answers, list) or len(answers) != 3:
        return jsonify({'success': False, 'message': '答案格式不正确'}), 400
    
    # 连接数据库
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 查询用户和重置令牌
        cursor.execute("""
        SELECT id, security_questions, reset_token, reset_token_expires 
        FROM users 
        WHERE id = %s AND reset_token = %s
        """, (user_id, reset_token))
        
        user = cursor.fetchone()
        
        # 验证用户和令牌存在
        if not user:
            return jsonify({'success': False, 'message': '无效的用户或重置令牌'}), 400
        
        # 验证令牌是否过期
        if user['reset_token_expires'] < datetime.now():
            return jsonify({'success': False, 'message': '重置令牌已过期，请重新开始'}), 400
        
        # 验证密保问题答案
        stored_questions = json.loads(user['security_questions'])
        correct_answers = 0
        
        for i, answer_data in enumerate(answers):
            if i >= len(stored_questions):
                break
                
            user_answer = answer_data.get('answer', '').strip().lower()
            stored_answer = stored_questions[i].get('answer', '').strip().lower()
            
            if user_answer == stored_answer:
                correct_answers += 1
        
        # 至少要回答对2个问题
        if correct_answers >= 2:
            # 生成验证成功令牌
            verification_token = uuid.uuid4().hex
            expires = datetime.now() + timedelta(minutes=15)  # 15分钟内必须重置密码
            
            # 更新验证令牌
            cursor.execute(
                "UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE id = %s",
                (verification_token, expires, user_id)
            )
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': '密保问题验证成功',
                'verificationToken': verification_token
            })
        else:
            return jsonify({
                'success': False,
                'message': '密保问题答案不正确',
                'correctCount': correct_answers
            }), 400
    except Error as e:
        logger.error(f"验证密保问题答案错误: {e}")
        return jsonify({'success': False, 'message': f'验证失败: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """重置密码"""
    data = request.get_json()
    
    if not data or 'userId' not in data or 'verificationToken' not in data or 'newPassword' not in data:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    user_id = data['userId']
    verification_token = data['verificationToken']
    new_password = data['newPassword']
    
    # 验证新密码强度
    valid_password, password_message = validate_password(new_password)
    if not valid_password:
        return jsonify({'success': False, 'message': password_message}), 400
    
    # 连接数据库
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 查询用户和验证令牌
        cursor.execute("""
        SELECT id, reset_token, reset_token_expires 
        FROM users 
        WHERE id = %s AND reset_token = %s
        """, (user_id, verification_token))
        
        user = cursor.fetchone()
        
        # 验证用户和令牌存在
        if not user:
            return jsonify({'success': False, 'message': '无效的用户或验证令牌'}), 400
        
        # 验证令牌是否过期
        if user['reset_token_expires'] < datetime.now():
            return jsonify({'success': False, 'message': '验证令牌已过期，请重新开始'}), 400
        
        # 生成新的密码哈希和盐值
        new_password_hash, new_salt = hash_password(new_password)
        
        # 更新密码并清除重置令牌
        cursor.execute(
            "UPDATE users SET password_hash = %s, salt = %s, reset_token = NULL, reset_token_expires = NULL WHERE id = %s",
            (new_password_hash, new_salt, user_id)
        )
        conn.commit()
        
        logger.info(f"用户ID {user_id} 已重置密码")
        return jsonify({
            'success': True,
            'message': '密码重置成功，请使用新密码登录'
        })
    except Error as e:
        logger.error(f"重置密码错误: {e}")
        return jsonify({'success': False, 'message': f'重置密码失败: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/admin/users', methods=['GET'])
def get_all_users():
    """管理员获取所有用户列表API"""
    # 获取请求头中的令牌
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'success': False, 'message': '未提供有效的访问令牌'}), 401
    
    # 验证令牌
    payload = verify_jwt_token(token)
    if not payload:
        return jsonify({'success': False, 'message': '访问令牌无效或已过期'}), 401
    
    # 验证用户是否为管理员或超级管理者
    if payload.get('role') != 'admin' and payload.get('role') != 'super_admin':
        return jsonify({'success': False, 'message': '权限不足，仅管理员可访问'}), 403
    
    # 连接到数据库
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 根据用户角色返回不同范围的用户
        if payload.get('role') == 'super_admin':
            # 超级管理者可以看到所有用户
            cursor.execute("""
            SELECT id, username, email, role, status, created_at, last_login, avatar
            FROM users ORDER BY created_at DESC
            """)
        else:
            # 普通管理员只能看到普通用户
            cursor.execute("""
            SELECT id, username, email, role, status, created_at, last_login, avatar
            FROM users 
            WHERE role = 'user' 
            ORDER BY created_at DESC
            """)
        
        users = cursor.fetchall()
        
        # 格式化日期
        for user in users:
            if user['created_at']:
                user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if user['last_login']:
                user['last_login'] = user['last_login'].strftime('%Y-%m-%d %H:%M:%S')
                
        return jsonify({'success': True, 'users': users})
    except Error as e:
        logger.error(f"获取用户列表错误: {e}")
        return jsonify({'success': False, 'message': f'获取用户列表失败: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/admin/users/<int:user_id>/status', methods=['PUT'])
def update_user_status(user_id):
    """更新用户状态"""
    # 获取JWT令牌
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'message': '未授权：缺少有效的认证令牌'}), 401
    
    token = auth_header.split(' ')[1]
    payload = verify_jwt_token(token)
    if not payload:
        return jsonify({'success': False, 'message': '未授权：令牌无效或已过期'}), 401
    
    current_user_id = payload['user_id']
    
    # 检查当前用户是否为管理员
    if not is_admin(current_user_id):
        return jsonify({'success': False, 'message': '权限不足：只有管理员可以更改用户状态'}), 403
    
    # 获取请求数据
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'success': False, 'message': '无效请求：缺少状态参数'}), 400
    
    new_status = data['status']
    
    # 验证状态有效性
    if new_status not in ['active', 'banned']:
        return jsonify({'success': False, 'message': '无效的状态值'}), 400
    
    # 禁止更改自己的状态
    if int(user_id) == current_user_id:
        return jsonify({'success': False, 'message': '不能更改自己的状态'}), 403
    
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 获取要更改状态的用户信息
        cursor.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        # 检查权限：超级管理者可以管理管理员账户，普通管理员不能
        is_current_user_super_admin = is_super_admin(current_user_id)
        
        # 如果目标用户是管理员或超级管理者，只有超级管理者可以管理
        if (user['role'] == USER_ROLE_ADMIN or user['role'] == USER_ROLE_SUPER_ADMIN) and not is_current_user_super_admin:
            return jsonify({'success': False, 'message': '权限不足：普通管理员不能管理其他管理员'}), 403
        
        # 禁止修改超级管理者状态
        if user['role'] == USER_ROLE_SUPER_ADMIN:
            return jsonify({'success': False, 'message': '不能修改超级管理者的状态'}), 403
        
        # 更新用户状态
        cursor.execute("""
        UPDATE users SET status = %s WHERE id = %s
        """, (new_status, user_id))
        conn.commit()
        
        action = "解除封禁" if new_status == 'active' else "封禁"
        logger.info(f"管理员 {payload['username']} 已{action}用户 {user['username']}")
        
        return jsonify({
            'success': True, 
            'message': f'用户已{action}',
            'user_id': user_id,
            'new_status': new_status
        })
    except Error as e:
        logger.error(f"更新用户状态错误: {e}")
        return jsonify({'success': False, 'message': f'数据库错误: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 获取管理员数量函数
def get_admin_count():
    """获取当前管理员数量"""
    conn = connect_to_db()
    if not conn:
        logger.error("获取管理员数量失败：无法连接到数据库")
        return -1
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COUNT(*) FROM users WHERE role = %s AND status = 'active'
        """, (USER_ROLE_ADMIN,))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Error as e:
        logger.error(f"获取管理员数量错误: {e}")
        return -1
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 检查用户是否为超级管理者
def is_super_admin(user_id):
    """检查给定用户ID是否为超级管理者"""
    conn = connect_to_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT role FROM users WHERE id = %s
        """, (user_id,))
        result = cursor.fetchone()
        return result and result[0] == USER_ROLE_SUPER_ADMIN
    except Error as e:
        logger.error(f"检查超级管理者权限错误: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 检查用户是否为普通管理员
def is_admin(user_id):
    """检查给定用户ID是否为管理员"""
    conn = connect_to_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT role FROM users WHERE id = %s
        """, (user_id,))
        result = cursor.fetchone()
        return result and (result[0] == USER_ROLE_ADMIN or result[0] == USER_ROLE_SUPER_ADMIN)
    except Error as e:
        logger.error(f"检查管理员权限错误: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 添加新API接口：更改用户角色
@app.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
def update_user_role(user_id):
    """
    更改用户角色API
    超级管理者可以将普通用户升级为管理员或将管理员降级为普通用户
    """
    # 获取JWT令牌
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'message': '未授权：缺少有效的认证令牌'}), 401
    
    token = auth_header.split(' ')[1]
    payload = verify_jwt_token(token)
    if not payload:
        return jsonify({'success': False, 'message': '未授权：令牌无效或已过期'}), 401
    
    current_user_id = payload['user_id']
    
    # 检查当前用户是否为超级管理者
    if not is_super_admin(current_user_id):
        return jsonify({'success': False, 'message': '权限不足：只有超级管理者可以更改用户角色'}), 403
    
    # 获取请求数据
    data = request.get_json()
    if not data or 'role' not in data:
        return jsonify({'success': False, 'message': '无效请求：缺少角色参数'}), 400
    
    new_role = data['role']
    
    # 验证角色有效性
    if new_role not in [USER_ROLE_ADMIN, USER_ROLE_USER]:
        return jsonify({'success': False, 'message': '无效的角色值'}), 400
    
    # 禁止修改超级管理者的角色
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 检查要修改的用户是否存在
        cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        # 禁止修改超级管理者
        if user['role'] == USER_ROLE_SUPER_ADMIN:
            return jsonify({'success': False, 'message': '不能修改超级管理者的角色'}), 403
        
        # 如果是设置为管理员，检查管理员数量是否达到上限
        if new_role == USER_ROLE_ADMIN and user['role'] != USER_ROLE_ADMIN:
            admin_count = get_admin_count()
            if admin_count >= MAX_ADMIN_COUNT:
                return jsonify({'success': False, 'message': f'管理员数量已达到上限 ({MAX_ADMIN_COUNT})'}), 400
        
        # 更新用户角色
        cursor.execute("""
        UPDATE users SET role = %s WHERE id = %s
        """, (new_role, user_id))
        conn.commit()
        
        return jsonify({
            'success': True, 
            'message': f'用户角色已更新为 {new_role}',
            'user_id': user_id,
            'new_role': new_role
        })
    except Error as e:
        logger.error(f"更新用户角色错误: {e}")
        return jsonify({'success': False, 'message': f'数据库错误: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 获取管理员列表API
@app.route('/api/admin/admins', methods=['GET'])
def get_admin_list():
    """获取所有管理员列表"""
    # 获取JWT令牌
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'message': '未授权：缺少有效的认证令牌'}), 401
    
    token = auth_header.split(' ')[1]
    payload = verify_jwt_token(token)
    if not payload:
        return jsonify({'success': False, 'message': '未授权：令牌无效或已过期'}), 401
    
    current_user_id = payload['user_id']
    
    # 检查当前用户是否为超级管理者
    if not is_super_admin(current_user_id):
        return jsonify({'success': False, 'message': '权限不足：只有超级管理者可以查看管理员列表'}), 403
    
    conn = connect_to_db()
    if not conn:
        return jsonify({'success': False, 'message': '服务器错误：无法连接到数据库'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 查询所有管理员
        cursor.execute("""
        SELECT id, username, email, role, status, created_at, last_login 
        FROM users 
        WHERE role IN (%s, %s)
        ORDER BY role DESC, id ASC
        """, (USER_ROLE_SUPER_ADMIN, USER_ROLE_ADMIN))
        
        admins = cursor.fetchall()
        
        # 格式化日期时间
        for admin in admins:
            if 'created_at' in admin and admin['created_at']:
                admin['created_at'] = admin['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if 'last_login' in admin and admin['last_login']:
                admin['last_login'] = admin['last_login'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'admins': admins,
            'admin_count': sum(1 for admin in admins if admin['role'] == USER_ROLE_ADMIN),
            'max_admin_count': MAX_ADMIN_COUNT
        })
    except Error as e:
        logger.error(f"获取管理员列表错误: {e}")
        return jsonify({'success': False, 'message': f'数据库错误: {str(e)}'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 添加健康检查接口
@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'success',
        'message': '用户认证服务运行正常',
        'time': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    })

# 添加健康检查路由OPTIONS预检请求处理
@app.route('/api/health', methods=['OPTIONS'])
def handle_health_options():
    resp = app.make_default_options_response()
    headers = resp.headers
    headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Cache-Control, pragma'
    headers['Access-Control-Allow-Origin'] = 'http://localhost:3001'
    headers['Access-Control-Allow-Credentials'] = 'true'
    return resp

def start_server():
    """启动服务器"""
    # 初始化数据库
    init_database()
    
    # 获取日志级别
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # 设置新的日志级别
    if log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        logger.setLevel(getattr(logging, log_level))
        logger.info(f"日志级别设置为: {log_level}")
    
    # 设置服务器端口
    port = int(os.environ.get('AUTH_API_PORT', 5004))
    
    # 启动服务器
    logger.info(f"启动用户认证API服务器 - 端口: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    start_server() 