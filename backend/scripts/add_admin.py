#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
添加管理员账号脚本
允许通过命令行添加或设置管理员账号
"""

import sys
import os
import mysql.connector
import hashlib
import uuid
import argparse
from pathlib import Path

# 设置项目根目录
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '20040102a',
    'database': 'air_quality_monitoring',
    'port': 3306
}

def connect_to_db():
    """连接到数据库"""
    try:
        print("正在连接到数据库...")
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            print("数据库连接成功")
            return conn
        print("数据库连接失败：未能建立连接")
        return None
    except Exception as e:
        print(f"数据库连接错误: {e}")
        return None

def hash_password(password, salt=None):
    """使用SHA256对密码进行哈希"""
    if salt is None:
        salt = uuid.uuid4().hex
    
    # 组合密码和盐值进行哈希
    hash_obj = hashlib.sha256()
    hash_obj.update((password + salt).encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    
    return password_hash, salt

def add_admin_user(username, password, email):
    """添加管理员用户"""
    conn = connect_to_db()
    if not conn:
        print("无法连接到数据库，操作失败")
        return False
    
    try:
        cursor = conn.cursor()
        
        # 检查用户是否已存在
        cursor.execute("SELECT id, role FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        password_hash, salt = hash_password(password)
        
        if user:
            user_id, current_role = user
            
            # 用户存在，更新为管理员
            if current_role == 'admin':
                print(f"用户 {username} 已经是管理员")
                return True
                
            cursor.execute("""
            UPDATE users 
            SET role = 'admin', password_hash = %s, salt = %s, email = %s
            WHERE id = %s
            """, (password_hash, salt, email, user_id))
            
            conn.commit()
            print(f"用户 {username} 已更新为管理员")
            return True
        else:
            # 用户不存在，创建新管理员用户
            cursor.execute("""
            INSERT INTO users (username, email, password_hash, salt, role)
            VALUES (%s, %s, %s, %s, 'admin')
            """, (username, email, password_hash, salt))
            
            conn.commit()
            print(f"管理员用户 {username} 创建成功")
            return True
    except Exception as e:
        print(f"添加管理员用户时出错: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='添加或设置管理员账号')
    parser.add_argument('--username', default='12306', help='管理员用户名')
    parser.add_argument('--password', default='888888', help='管理员密码')
    parser.add_argument('--email', default='1438300952@qq.com', help='管理员邮箱')
    
    args = parser.parse_args()
    
    if add_admin_user(args.username, args.password, args.email):
        print("管理员账号设置成功")
    else:
        print("管理员账号设置失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 