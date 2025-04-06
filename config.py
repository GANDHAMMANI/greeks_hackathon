# config.py - Configuration file

import os
from datetime import timedelta

# Flask configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size for uploads
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}

# Session configuration
PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

# Admin credentials (should be stored securely in production)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'password')

# Database configurations
# MySQL
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'job')

# Neo4j
NEO4J_URI = os.getenv('NEO4J_URI', 'neo4j+s://aaa466f7.databases.neo4j.io')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', '7aVotGMFzl62FgbDKqFU7tunpMJOyHPxWPHTiyrWnxw')