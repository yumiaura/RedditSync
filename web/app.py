"""Flask web interface for Reddit Sync using SQLAlchemy ORM.

This module provides a web interface for browsing downloaded Reddit content.
Uses SQLAlchemy ORM for database operations and supports various media types.
"""
import asyncio
import io
import mimetypes
import os
from pathlib import Path
import sys

from flask import Flask, render_template, send_from_directory, url_for, redirect, send_file, abort
from PIL import Image, ImageDraw, ImageFont
import magic
import fitz  # PyMuPDF for PDF processing

# Add the app directory to Python path for ORM imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app import db
from app.models import News, Media, Subscription

app = Flask(__name__)

# Configuration
MEDIA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'media'))
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'db.sqlite'))

# Global variable to track if database is initialized
_db_initialized = False


async def ensure_db_initialized():
    """Ensure database is initialized for web interface."""
    global _db_initialized
    if not _db_initialized:
        await db.init_db(DB_PATH)
        _db_initialized = True


def run_async(coro):
    """Helper to run async functions in Flask routes."""
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


@app.route('/')
def index():
    """Main page showing list of news items."""
    async def get_news_data():
        await ensure_db_initialized()
        # Get all news items ordered by newest first
        async with db.get_session() as session:
            from sqlalchemy import select
            stmt = select(News).order_by(News.added_at.desc()).limit(100)
            result = await session.execute(stmt)
            news_items = result.scalars().all()
            
            return [
                {
                    'id': item.id,
                    'title': item.title or 'No title',
                    'external_id': item.external_id,
                    'media_uid': item.media_uid,
                    'author': item.author,
                    'added_at': item.added_at,
                    'thread_id': item.thread_id
                }
                for item in news_items
            ]
    
    news = run_async(get_news_data())
    return render_template('index.html', news=news)


@app.route('/news/<int:news_id>')
def news_detail(news_id):
    """Detail page for a specific news item."""
    async def get_news_detail():
        await ensure_db_initialized()
        async with db.get_session() as session:
            from sqlalchemy import select
            stmt = select(News).where(News.id == news_id)
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()
            
            if item:
                return {
                    'id': item.id,
                    'title': item.title,
                    'body': item.body,
                    'author': item.author,
                    'external_id': item.external_id,
                    'media_uid': item.media_uid,
                    'media_url': item.media_url,
                    'created_utc': item.created_utc,
                    'added_at': item.added_at,
                    'thread_id': item.thread_id,
                    'raw_json': item.raw_json
                }
            return None
    
    item = run_async(get_news_detail())
    if not item:
        abort(404)
    
    media_url = None
    if item['media_uid']:
        media_url = url_for('media_file', filename=item['media_uid'])
    
    return render_template('detail.html', item=item, media_url=media_url)


@app.route('/subscriptions')
def subscriptions():
    """Page showing all subscriptions."""
    async def get_subscriptions_data():
        await ensure_db_initialized()
        async with db.get_session() as session:
            from sqlalchemy import select
            stmt = select(Subscription).order_by(Subscription.added_at.desc())
            result = await session.execute(stmt)
            subs = result.scalars().all()
            
            return [
                {
                    'id': sub.id,
                    'thread_id': sub.thread_id,
                    'title': sub.title,
                    'added_at': sub.added_at
                }
                for sub in subs
            ]
    
    subs = run_async(get_subscriptions_data())
    return render_template('subscriptions.html', subscriptions=subs)


@app.route('/media/<path:filename>')
def media_file(filename):
    """Serve media files with appropriate processing."""
    file_path = os.path.join(MEDIA_DIR, filename)
    
    if not os.path.exists(file_path):
        abort(404)
    
    # Check file mime-type
    mime = magic.Magic(mime=True).from_file(file_path)
    
    # For images and videos return as is
    if mime and (mime.startswith('image/') or mime.startswith('video/')):
        return send_from_directory(MEDIA_DIR, filename)
    
    # For HTML and .bin files with HTML content
    if mime == 'text/html' or filename.endswith('.bin'):
        # List of encodings to check
        encodings = ['utf-8', 'latin1', 'cp1251', 'iso-8859-1']
        html_markers = ['<!DOCTYPE html>', '<html', '<head>', '<body>', '<div', '<p>']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # Check various HTML content markers
                    if any(marker in content.lower() for marker in html_markers):
                        return content, {'Content-Type': f'text/html; charset={encoding}'}
            except UnicodeDecodeError:
                continue  # Try next encoding
    
    # For PDF files generate preview of first page
    if mime == 'application/pdf':
        try:
            pdf_document = fitz.open(file_path)
            if pdf_document.page_count > 0:
                page = pdf_document[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for quality
                img_data = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                buf = io.BytesIO()
                img_data.save(buf, format='PNG')
                buf.seek(0)
                return send_file(buf, mimetype='image/png')
        except Exception as e:
            print(f"PDF conversion error: {e}")
    
    try:
        # Try to open as image
        with Image.open(file_path) as img:
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return send_file(buf, mimetype='image/png')
    except Exception:
        # If nothing worked, generate preview with file information
        img = Image.new('RGB', (400, 200), color=(200, 200, 200))
        d = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        text = f'File: {filename}\nType: {mime}'
        d.multiline_text((10, 80), text, fill=(0, 0, 0), font=font, align='center')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')


@app.route('/back')
def go_back():
    """Go back to main page."""
    return redirect(url_for('index'))


@app.teardown_appcontext
def close_db_connections(error):
    """Clean up database connections."""
    if _db_initialized:
        try:
            run_async(db.close_db())
        except Exception as e:
            print(f"Error closing database connections: {e}")


if __name__ == '__main__':
    app.run(debug=True)
